param(
    [string[]]$PytestArguments = @('tests/test_app_009.py', '--tb=no', '-q'),
    [int]$Port = 55439,
    [ValidateSet('app009_test', 'app009_acceptance')]
    [string]$DatabaseName = 'app009_test',
    [switch]$MigrateOnly,
    [string]$PostgresBin = 'C:\Program Files\PostgreSQL\17\bin'
)

$ErrorActionPreference = 'Stop'
$backendDirectory = Split-Path $PSScriptRoot -Parent
$projectDirectory = Split-Path $backendDirectory -Parent
# Keep the synthetic cluster outside TEMP: Windows cleanup can remove PG_VERSION
# and root configuration files from a running cluster overnight.
$clusterDirectory = Join-Path $env:LOCALAPPDATA "job-app009-postgres-$Port"
$dataDirectory = Join-Path $clusterDirectory 'data'
$logFile = Join-Path $clusterDirectory 'server.log'
$pgCtl = Join-Path $PostgresBin 'pg_ctl.exe'
if (-not (Test-Path -LiteralPath $pgCtl)) { throw "PostgreSQL tools unavailable: $PostgresBin" }
New-Item -ItemType Directory -Force -Path $clusterDirectory | Out-Null

if (-not (Test-Path -LiteralPath (Join-Path $dataDirectory 'PG_VERSION'))) {
    & (Join-Path $PostgresBin 'initdb.exe') -D $dataDirectory -U app009_test --auth=trust --encoding=UTF8 --locale=C
    if ($LASTEXITCODE -ne 0) { throw 'Isolated PostgreSQL initialization failed.' }
}
& $pgCtl -D $dataDirectory status | Out-Null
if ($LASTEXITCODE -ne 0) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try { $listener.Start() } finally { $listener.Stop() }
    $startArguments = @('-D', ('"' + $dataDirectory + '"'), '-l', ('"' + $logFile + '"'), '-o', ('"-h 127.0.0.1 -p ' + $Port + '"'), '-w', 'start')
    $process = Start-Process -FilePath $pgCtl -ArgumentList $startArguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $clusterDirectory 'startup.out') -RedirectStandardError (Join-Path $clusterDirectory 'startup.err')
    # -Wait also follows the long-lived postgres descendant on Windows.
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "Isolated PostgreSQL startup failed; inspect $clusterDirectory startup logs." }
}

# Every value is synthetic and only applies to this command's child process.
$oldDatabaseUrl = $env:DATABASE_URL
$oldSecretKey = $env:DJANGO_SECRET_KEY
$env:DATABASE_URL = "postgresql://app009_test@127.0.0.1:$Port/$DatabaseName"
$env:DJANGO_SECRET_KEY = 'app009-isolated-test-only-secret-key-2026-not-for-production'
try {
    $existing = & (Join-Path $PostgresBin 'psql.exe') -h 127.0.0.1 -p $Port -U app009_test -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DatabaseName'"
    if ($LASTEXITCODE -ne 0) { throw 'Isolated PostgreSQL probe failed.' }
    if ($existing -ne '1') {
        & (Join-Path $PostgresBin 'createdb.exe') -h 127.0.0.1 -p $Port -U app009_test $DatabaseName
        if ($LASTEXITCODE -ne 0) { throw 'Test base database creation failed.' }
    }
    Push-Location $backendDirectory
    try {
        $pythonVersion = (Get-Content -LiteralPath (Join-Path $projectDirectory '.python-version') -Raw).Trim()
        & uv sync --frozen --group test --python $pythonVersion
        if ($LASTEXITCODE -ne 0) { throw 'Frozen test dependency sync failed.' }
        & uv run --no-sync python --version
        if ($MigrateOnly) {
            & uv run --no-sync python manage.py migrate --noinput
            $testExitCode = $LASTEXITCODE
        } else {
            & uv run --no-sync pytest @PytestArguments
            $testExitCode = $LASTEXITCODE
        }
    } finally { Pop-Location }
} finally {
    $env:DATABASE_URL = $oldDatabaseUrl
    $env:DJANGO_SECRET_KEY = $oldSecretKey
}
exit $testExitCode
