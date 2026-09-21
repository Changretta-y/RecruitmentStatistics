param(
    [Parameter(Mandatory = $true)] [string] $DatabaseUrl,
    [Parameter(Mandatory = $true)] [string] $RestoreDatabaseUrl,
    [Parameter(Mandatory = $true)] [string] $BackupFile,
    [string] $PgBin = 'C:\Program Files\PostgreSQL\17\bin'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectRoot = Split-Path -Parent $PSScriptRoot

foreach ($tool in @('pg_dump.exe', 'pg_restore.exe', 'psql.exe', 'createdb.exe', 'dropdb.exe')) {
    $path = Join-Path $PgBin $tool
    if (-not (Test-Path -LiteralPath $path)) {
        throw "PostgreSQL client tool is missing: $path"
    }
}

$pgDump = Join-Path $PgBin 'pg_dump.exe'
$pgRestore = Join-Path $PgBin 'pg_restore.exe'
$psql = Join-Path $PgBin 'psql.exe'
$createdb = Join-Path $PgBin 'createdb.exe'
$dropdb = Join-Path $PgBin 'dropdb.exe'

Write-Output '== backup =='
& $pgDump --dbname=$DatabaseUrl --format=custom --file=$BackupFile
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed with exit code $LASTEXITCODE" }

Write-Output '== migrations =='
Push-Location $projectRoot
uv run --project backend python backend/manage.py migrate --plan
Pop-Location
if ($LASTEXITCODE -ne 0) { throw "migration plan failed with exit code $LASTEXITCODE" }

$restoreUri = [Uri]$RestoreDatabaseUrl
$restoreDb = $restoreUri.AbsolutePath.Trim('/').Split('?')[0]
$restoreServer = $RestoreDatabaseUrl -replace ('/' + [regex]::Escape($restoreDb) + '$'), '/postgres'

Write-Output "== restore to isolated database: $restoreDb =="
& $dropdb --if-exists --maintenance-db=$restoreServer $restoreDb
& $createdb --maintenance-db=$restoreServer $restoreDb
& $pgRestore --clean --if-exists --dbname=$RestoreDatabaseUrl $BackupFile
if ($LASTEXITCODE -ne 0) { throw "pg_restore failed with exit code $LASTEXITCODE" }

Write-Output '== restored data probe =='
$probe = & $psql --dbname=$RestoreDatabaseUrl --tuples-only --no-align --command='SELECT COUNT(*) FROM job_applications;'
if ($LASTEXITCODE -ne 0) { throw "restored data probe failed with exit code $LASTEXITCODE" }
Write-Output ("restored applications rows: " + $probe.Trim())
Write-Output 'release rehearsal completed'
