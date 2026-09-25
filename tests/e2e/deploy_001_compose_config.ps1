param(
    [string]$SshHost = $(if ($env:DEPLOY_TEST_SSH_HOST) { $env:DEPLOY_TEST_SSH_HOST } else { "huoshan" }),
    [string]$ComposePath = "",
    [string]$JenkinsPath = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $ComposePath) { $ComposePath = Join-Path $repoRoot "docker-compose.yml" }
if (-not $JenkinsPath) { $JenkinsPath = Join-Path $repoRoot "Jenkinsfile" }
$guid = [Guid]::NewGuid().ToString("N")
$remoteDir = "/tmp/deploy-001-test-$guid"
$tempFiles = [System.Collections.Generic.List[string]]::new()
$failures = [System.Collections.Generic.List[string]]::new()

function Invoke-Ssh([string]$RemoteCommand) {
    $result = @(& ssh -o BatchMode=yes -o ConnectTimeout=10 $SshHost $RemoteCommand 2>$null)
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 255) { throw "SSH transport failed for the configured deployment test host." }
    return [pscustomobject]@{ ExitCode = $exitCode; Output = ($result -join "`n") }
}

function Get-Config([string]$EnvName, [string]$Profile = "") {
    $profileOption = ""
    if ($Profile) { $profileOption = "--profile '$Profile' " }
    $cmd = "cd '$remoteDir' && env -u DJANGO_SECRET_KEY -u POSTGRES_PASSWORD -u EMAIL_HOST -u EMAIL_PORT -u EMAIL_HOST_USER -u EMAIL_HOST_PASSWORD -u EMAIL_USE_TLS -u EMAIL_USE_SSL -u DEFAULT_FROM_EMAIL -u FRONTEND_BASE_URL -u DJANGO_ALLOWED_HOSTS -u CORS_ALLOWED_ORIGINS -u ENABLE_DAILY_EMAILS -u COMPOSE_PROFILES docker compose --project-directory '$remoteDir' --env-file '$remoteDir/$EnvName' $profileOption config --format json"
    $result = Invoke-Ssh $cmd
    if ($result.ExitCode -ne 0) { return $null }
    try { return ($result.Output | ConvertFrom-Json) } catch { return $null }
}

function Get-Service($Config, [string]$Name) {
    if ($null -eq $Config -or $null -eq $Config.services) { return $null }
    $property = $Config.services.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Get-EnvironmentValue($Service, [string[]]$Names) {
    if ($null -eq $Service -or $null -eq $Service.environment) { return $null }
    foreach ($name in $Names) {
        $property = $Service.environment.PSObject.Properties[$name]
        if ($null -ne $property) { return [string]$property.Value }
    }
    return $null
}

function Assert-Result([string]$Name, [bool]$Passed) {
    if ($Passed) {
        Write-Output "PASS $Name"
    } else {
        Write-Output "FAIL $Name"
        $failures.Add($Name)
    }
}

try {
    if (-not (Get-Command ssh -ErrorAction SilentlyContinue) -or -not (Get-Command scp -ErrorAction SilentlyContinue)) {
        throw "OpenSSH client is required for the remote Compose config check."
    }
    if (-not (Test-Path -LiteralPath $ComposePath) -or -not (Test-Path -LiteralPath $JenkinsPath)) {
        throw "Public Compose and Jenkins configuration files are required."
    }

    $created = Invoke-Ssh "umask 077 && mkdir -m 700 -- '$remoteDir'"
    if ($created.ExitCode -ne 0) { throw "Could not create an isolated remote temporary directory." }
    Write-Output "Remote temporary directory: $remoteDir"
    & scp -q -o BatchMode=yes $ComposePath "${SshHost}:$remoteDir/docker-compose.yml"
    if ($LASTEXITCODE -ne 0) { throw "Could not copy the public Compose configuration to the isolated temporary directory." }
    & scp -q -o BatchMode=yes $JenkinsPath "${SshHost}:$remoteDir/Jenkinsfile"
    if ($LASTEXITCODE -ne 0) { throw "Could not copy public deployment configuration to the isolated temporary directory." }

    $noSecretsFile = [System.IO.Path]::GetTempFileName()
    $noMailFile = [System.IO.Path]::GetTempFileName()
    $mailEnabledFile = [System.IO.Path]::GetTempFileName()
    $tempFiles.Add($noSecretsFile); $tempFiles.Add($noMailFile); $tempFiles.Add($mailEnabledFile)

    $common = @(
        "DJANGO_ALLOWED_HOSTS=115.190.240.84,localhost,127.0.0.1",
        "CORS_ALLOWED_ORIGINS=http://115.190.240.84:5173",
        "FRONTEND_BASE_URL=http://115.190.240.84:5173",
        "FRONTEND_PORT=5173"
    )
    [System.IO.File]::WriteAllText($noSecretsFile, ($common -join "`n") + "`n", [System.Text.UTF8Encoding]::new($false))

    $fakeSecrets = @("DJANGO_SECRET_KEY=DEPLOY001-FAKE-DJANGO-ONLY", "POSTGRES_PASSWORD=DEPLOY001-FAKE-DB-URL_SAFE-5421")
    $noMail = @($fakeSecrets + $common + "ENABLE_DAILY_EMAILS=false")
    [System.IO.File]::WriteAllText($noMailFile, ($noMail -join "`n") + "`n", [System.Text.UTF8Encoding]::new($false))

    $smtpFake = @(
        "EMAIL_HOST=smtp.invalid.example",
        "EMAIL_PORT=2525",
        "EMAIL_HOST_USER=deploy001-fake-user",
        "EMAIL_HOST_PASSWORD=DEPLOY001-FAKE-SMTP-ONLY",
        "EMAIL_USE_TLS=true",
        "EMAIL_USE_SSL=false",
        "DEFAULT_FROM_EMAIL=notifications@invalid.example"
    )
    $mailEnabled = @($fakeSecrets + $common + $smtpFake + "ENABLE_DAILY_EMAILS=true")
    [System.IO.File]::WriteAllText($mailEnabledFile, ($mailEnabled -join "`n") + "`n", [System.Text.UTF8Encoding]::new($false))

    & scp -q -o BatchMode=yes $noSecretsFile "${SshHost}:$remoteDir/no-secrets.env"
    if ($LASTEXITCODE -ne 0) { throw "Could not copy synthetic missing-secret test input." }
    & scp -q -o BatchMode=yes $noMailFile "${SshHost}:$remoteDir/no-mail.env"
    if ($LASTEXITCODE -ne 0) { throw "Could not copy synthetic no-mail test input." }
    & scp -q -o BatchMode=yes $mailEnabledFile "${SshHost}:$remoteDir/mail-enabled.env"
    if ($LASTEXITCODE -ne 0) { throw "Could not copy synthetic SMTP test input." }

    $missingSecretsResult = Invoke-Ssh "cd '$remoteDir' && env -u DJANGO_SECRET_KEY -u POSTGRES_PASSWORD -u EMAIL_HOST -u EMAIL_PORT -u EMAIL_HOST_USER -u EMAIL_HOST_PASSWORD -u EMAIL_USE_TLS -u EMAIL_USE_SSL -u DEFAULT_FROM_EMAIL -u FRONTEND_BASE_URL -u DJANGO_ALLOWED_HOSTS -u CORS_ALLOWED_ORIGINS -u ENABLE_DAILY_EMAILS -u COMPOSE_PROFILES docker compose --project-directory '$remoteDir' --env-file '$remoteDir/no-secrets.env' config --quiet"
    Assert-Result "missing DJANGO_SECRET_KEY/POSTGRES_PASSWORD rejects Compose config" ($missingSecretsResult.ExitCode -ne 0)

    $noMailConfig = Get-Config "no-mail.env"
    $noMailScheduler = Get-Service $noMailConfig "scheduler"
    $enabledConfig = Get-Config "mail-enabled.env" "daily-email"
    $scheduler = Get-Service $enabledConfig "scheduler"
    $schedulerProfiles = @()
    if ($null -ne $scheduler -and $null -ne $scheduler.profiles) { $schedulerProfiles = @($scheduler.profiles) }
    $jenkinsText = [System.IO.File]::ReadAllText($JenkinsPath)
    $disabledBranch = [regex]::Match($jenkinsText, '(?s)else\s*\r?\n(.*?)\r?\n\s*fi')
    $noMailStopsScheduler = $false
    if ($disabledBranch.Success) {
        $disabledText = $disabledBranch.Groups[1].Value
        $plainUp = $false
        foreach ($line in ($disabledText -split "`r?`n")) {
            if ($line -match "docker compose" -and $line -match "up -d --remove-orphans" -and $line -notmatch "--profile") { $plainUp = $true }
        }
        $noMailStopsScheduler = $disabledText.Contains("stop scheduler") -and $disabledText.Contains("rm -f scheduler") -and $plainUp
    }
    $noMailBranchGated = $jenkinsText.Contains("ENABLE_DAILY_EMAILS") -and $noMailStopsScheduler
    Assert-Result "SMTP absent keeps daily-email gated and Jenkins stops/removes scheduler without enabling its profile" ($null -eq $noMailScheduler -and $schedulerProfiles -contains "daily-email" -and $noMailBranchGated)

    $backend = Get-Service $enabledConfig "backend"
    $expectedMail = @(
        @{ Names = @("EMAIL_HOST"); Value = "smtp.invalid.example" },
        @{ Names = @("EMAIL_PORT"); Value = "2525" },
        @{ Names = @("EMAIL_HOST_USER"); Value = "deploy001-fake-user" },
        @{ Names = @("EMAIL_HOST_PASSWORD"); Value = "DEPLOY001-FAKE-SMTP-ONLY" },
        @{ Names = @("EMAIL_USE_TLS"); Value = "true" },
        @{ Names = @("EMAIL_USE_SSL"); Value = "false" },
        @{ Names = @("DEFAULT_FROM_EMAIL"); Value = "notifications@invalid.example" },
        @{ Names = @("FRONTEND_BASE_URL"); Value = "http://115.190.240.84:5173" }
    )
    $mailVariablesCorrect = $null -ne $backend
    foreach ($item in $expectedMail) {
        if ((Get-EnvironmentValue $backend $item.Names) -ne $item.Value -or (Get-EnvironmentValue $scheduler $item.Names) -ne $item.Value) { $mailVariablesCorrect = $false }
    }
    Assert-Result "SMTP and HTTP origin variables reach backend with configured values" $mailVariablesCorrect

    $schedulerCommand = ""
    if ($null -ne $scheduler -and $null -ne $scheduler.command) { $schedulerCommand = ($scheduler.command | Out-String) }
    $schedulerImageConfigured = $null -ne $scheduler -and ($null -ne $scheduler.image -or $null -ne $scheduler.build)
    $sameImage = $null -ne $backend -and $null -ne $scheduler -and $scheduler.image -eq $backend.image
    $pipelineControlsProfile = $jenkinsText.Contains("ENABLE_DAILY_EMAILS") -and $jenkinsText.Contains("--profile daily-email up")
    Assert-Result "enabled daily mail has an active daily-email profile, task command, shared image and Jenkins profile control" ($schedulerProfiles -contains "daily-email" -and $schedulerCommand -match "send_daily_summaries" -and $schedulerImageConfigured -and $sameImage -and $pipelineControlsProfile)
    $backendDependency = $null
    if ($null -ne $scheduler -and $null -ne $scheduler.depends_on) { $backendDependency = $scheduler.depends_on.PSObject.Properties["backend"] }
    $waitsForBackendMigrations = $null -ne $backendDependency -and $backendDependency.Value.condition -eq "service_healthy"
    Assert-Result "scheduler waits for healthy backend startup and database migrations" $waitsForBackendMigrations
    Assert-Result "release branch guard supports BRANCH_NAME and GIT_BRANCH" ($jenkinsText.Contains("BRANCH_NAME") -and $jenkinsText.Contains("GIT_BRANCH") -and $jenkinsText.Contains("release"))

    $httpAllowedHosts = Get-EnvironmentValue $backend @("DJANGO_ALLOWED_HOSTS")
    $httpCors = Get-EnvironmentValue $backend @("CORS_ALLOWED_ORIGINS")
    $httpBase = Get-EnvironmentValue $backend @("FRONTEND_BASE_URL")
    $sslRedirect = Get-EnvironmentValue $backend @("SECURE_SSL_REDIRECT")
    $hstsSeconds = Get-EnvironmentValue $backend @("SECURE_HSTS_SECONDS")
    $sessionCookieSecure = Get-EnvironmentValue $backend @("SESSION_COOKIE_SECURE")
    $csrfCookieSecure = Get-EnvironmentValue $backend @("CSRF_COOKIE_SECURE")
    $httpEnabled = $httpAllowedHosts -match "(^|,)115\.190\.240\.84(,|$)" -and $httpCors -match "http://115\.190\.240\.84:5173" -and $httpBase -eq "http://115.190.240.84:5173" -and $sslRedirect -eq "false" -and $hstsSeconds -eq "0" -and $sessionCookieSecure -eq "false" -and $csrfCookieSecure -eq "false"
    Assert-Result "HTTP IP is allowed without SSL redirect, HSTS, or secure cookies" $httpEnabled
} finally {
    foreach ($file in $tempFiles) { Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue }
    if ($remoteDir -match '^/tmp/deploy-001-test-[0-9a-f]{32}$') {
        $null = Invoke-Ssh "rm -rf -- '$remoteDir'"
    }
}

if ($failures.Count -gt 0) {
    Write-Output "$($failures.Count) DEPLOY-001 configuration checks failed. No Compose services were started or modified."
    exit 1
}

Write-Output "All DEPLOY-001 configuration checks passed. No Compose services were started or modified."
exit 0
