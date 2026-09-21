$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$backendRoot = 'G:\job\backend'
$runserverArgs = 'manage.py runserver 127.0.0.1:8000'

function Get-LocalBackendProcesses {
    @(Get-CimInstance -ClassName Win32_Process | Where-Object {
        $_.ProcessId -ne $PID -and $_.Name -eq 'python.exe' -and $_.CommandLine -and
        $_.CommandLine.IndexOf($backendRoot, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -and
        $_.CommandLine.IndexOf($runserverArgs, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
    })
}

$targets = @(Get-LocalBackendProcesses)
if ($targets.Count -eq 0) { throw 'No local backend process matched the requested project and runserver command.' }
$targetPids = @($targets | ForEach-Object { [int]$_.ProcessId })
$uvPids = [System.Collections.Generic.List[int]]::new()
foreach ($target in $targets) {
    $parentId = [int]$target.ParentProcessId
    while ($parentId -ne 0) {
        $parent = Get-CimInstance -ClassName Win32_Process -Filter ('ProcessId = ' + $parentId)
        if (-not $parent) { break }
        if ($parent.Name -eq 'uv.exe' -and $parent.CommandLine -and $parent.CommandLine.IndexOf('run python ' + $runserverArgs, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            if (-not $uvPids.Contains([int]$parent.ProcessId)) { $uvPids.Add([int]$parent.ProcessId) }
            break
        }
        $parentId = [int]$parent.ParentProcessId
    }
}
foreach ($targetPid in $targetPids) { if (Get-Process -Id $targetPid -ErrorAction SilentlyContinue) { Stop-Process -Id $targetPid -Force -ErrorAction Stop } }
foreach ($uvPid in $uvPids) { if (Get-Process -Id $uvPid -ErrorAction SilentlyContinue) { Stop-Process -Id $uvPid -Force -ErrorAction Stop } }
$stopDeadline = (Get-Date).AddSeconds(10)
while ((Get-Date) -lt $stopDeadline) {
    $remaining = @(Get-LocalBackendProcesses)
    if ($remaining.Count -eq 0) { break }
    Start-Sleep -Milliseconds 250
}
if ($remaining.Count -ne 0) { throw 'A matched local backend process did not stop within the safety timeout.' }

$previousDatabaseUrl = $env:DATABASE_URL
$previousDjangoSecretKey = $env:DJANGO_SECRET_KEY
$previousDjangoDebug = $env:DJANGO_DEBUG
$previousCorsAllowedOrigins = $env:CORS_ALLOWED_ORIGINS
$env:DATABASE_URL = 'postgresql://postgres:postgres@127.0.0.1:5432/postgres'
$env:DJANGO_SECRET_KEY = 'e2e-only-development-secret-change-me'
$env:DJANGO_DEBUG = 'false'
$env:CORS_ALLOWED_ORIGINS = 'http://127.0.0.1:5182'

function Restore-TestEnvironment {
    if ($null -eq $previousDatabaseUrl) { Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue } else { $env:DATABASE_URL = $previousDatabaseUrl }
    if ($null -eq $previousDjangoSecretKey) { Remove-Item Env:DJANGO_SECRET_KEY -ErrorAction SilentlyContinue } else { $env:DJANGO_SECRET_KEY = $previousDjangoSecretKey }
    if ($null -eq $previousDjangoDebug) { Remove-Item Env:DJANGO_DEBUG -ErrorAction SilentlyContinue } else { $env:DJANGO_DEBUG = $previousDjangoDebug }
    if ($null -eq $previousCorsAllowedOrigins) { Remove-Item Env:CORS_ALLOWED_ORIGINS -ErrorAction SilentlyContinue } else { $env:CORS_ALLOWED_ORIGINS = $previousCorsAllowedOrigins }
}

try {
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = 'cmd.exe'
    $startInfo.WorkingDirectory = $backendRoot
    $startInfo.Arguments = '/d /c "uv run python manage.py runserver 127.0.0.1:8000"'
    $startInfo.UseShellExecute = $true
    $startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $server = [System.Diagnostics.Process]::Start($startInfo)

    $healthDeadline = (Get-Date).AddSeconds(30)
    $healthy = $false
    while ((Get-Date) -lt $healthDeadline) {
        try {
            $health = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/health/' -UseBasicParsing -TimeoutSec 2
            if ($server -and -not $server.HasExited -and [int]$health.StatusCode -eq 200) { $healthy = $true; break }
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    if (-not $healthy) {
        if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue }
        throw 'The restarted backend process did not remain alive or health did not return 200 within 30 seconds.'
    }
    Restore-TestEnvironment
} catch {
    Restore-TestEnvironment
    throw
}

Write-Output ('stopped local backend Python PID(s): ' + ($targetPids -join ','))
Write-Output ('started server PID: ' + $server.Id)
Write-Output 'health status: 200'
