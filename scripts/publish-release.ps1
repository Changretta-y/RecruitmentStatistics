param(
    [string]$GitHubRemote = 'origin',
    [string]$DeployRemote = 'deploy',
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$script:stage = 'validation'
$script:failureDetail = 'Command could not complete.'
$githubVerified = $false

function Invoke-ReleaseGit([string[]]$Arguments) {
    # Windows PowerShell turns native stderr into ErrorRecords. Capture it without
    # letting ErrorActionPreference terminate before the native exit code check.
    $ErrorActionPreference = 'Continue'
    $PSNativeCommandUseErrorActionPreference = $false
    $output = @(& $gitExe -C $repository @Arguments 2>&1)
    $nativeExitCode = $LASTEXITCODE
    if ($nativeExitCode -ne 0) {
        $script:failureDetail = "Git returned exit code $nativeExitCode. Check access, connectivity and remote history."
        throw 'Release Git command failed.'
    }
    # Native output can contain credentials in URLs or hook messages. Callers
    # inspect it in memory; the public output only uses our stage labels and SHA.
    return @($output | ForEach-Object { $_.ToString() })
}

function Get-ReleaseFetchUrl([string]$RemoteName, [string]$Label) {
    $script:stage = "$Label configuration"
    if ([string]::IsNullOrWhiteSpace($RemoteName) -or $remoteNames -cnotcontains $RemoteName) {
        $script:failureDetail = "$Label remote must exist."
        throw 'Invalid remote configuration.'
    }
    $urls = @(Invoke-ReleaseGit @('remote', 'get-url', '--all', $RemoteName))
    if ($urls.Count -ne 1 -or [string]::IsNullOrWhiteSpace($urls[0])) {
        $script:failureDetail = "$Label remote must have exactly one fetch URL."
        throw 'Ambiguous remote configuration.'
    }
    return $urls[0]
}

function Confirm-ReleaseRef([string]$Url, [string]$Label) {
    $script:stage = "$Label release verification"
    $refs = @(Invoke-ReleaseGit @('ls-remote', '--exit-code', '--refs', '--', $Url, 'refs/heads/release'))
    if ($refs.Count -ne 1 -or $refs[0] -notmatch '^([0-9a-fA-F]{40}|[0-9a-fA-F]{64})\s+refs/heads/release$' -or $Matches[1] -ne $sha) {
        $script:failureDetail = "$Label release does not match captured SHA $sha."
        throw 'Release verification failed.'
    }
    Write-Output "$Label release verified: $sha"
}

try {
    $gitExe = (Get-Command git -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    $repository = (Get-Location).ProviderPath
    $script:stage = 'release branch validation'
    $branch = @(Invoke-ReleaseGit @('symbolic-ref', '--quiet', 'HEAD'))
    if ($branch.Count -ne 1 -or $branch[0] -cne 'refs/heads/release') {
        $script:failureDetail = 'Run from the release branch; detached HEAD is not supported.'
        throw 'Invalid release branch.'
    }
    $head = @(Invoke-ReleaseGit @('rev-parse', '--verify', 'HEAD^{commit}'))
    if ($head.Count -ne 1 -or $head[0] -notmatch '^([0-9a-fA-F]{40}|[0-9a-fA-F]{64})$') {
        $script:failureDetail = 'A committed release HEAD is required.'
        throw 'Invalid release HEAD.'
    }
    $sha = $head[0]
    Write-Output "Captured release SHA: $sha"
    $remoteNames = @(Invoke-ReleaseGit @('remote'))
    $githubUrl = Get-ReleaseFetchUrl $GitHubRemote 'GitHub'
    $deployUrl = Get-ReleaseFetchUrl $DeployRemote 'deploy'
    $script:stage = 'destination validation'
    if ([string]::Equals($githubUrl, $deployUrl, [StringComparison]::Ordinal)) {
        $script:failureDetail = 'GitHub and deploy must have different fetch URLs.'
        throw 'Duplicate release destination.'
    }

    if ($DryRun) {
        Write-Output "DryRun: GitHub push and release verification -> deploy push -> verify both release refs at $sha."
        exit 0
    }

    $refspec = "${sha}:refs/heads/release"
    $script:stage = 'GitHub push'
    Invoke-ReleaseGit @('push', '--no-follow-tags', '--', $githubUrl, $refspec) | Out-Null
    Write-Output "GitHub push succeeded: $sha"
    Confirm-ReleaseRef $githubUrl 'GitHub'
    $githubVerified = $true

    $script:stage = 'deploy push'
    Invoke-ReleaseGit @('push', '--no-follow-tags', '--', $deployUrl, $refspec) | Out-Null
    Write-Output "deploy push succeeded: $sha"
    Confirm-ReleaseRef $githubUrl 'GitHub'
    Confirm-ReleaseRef $deployUrl 'deploy'
    Write-Output "SUCCESS: GitHub and deploy release both match captured SHA $sha."
    exit 0
} catch {
    Write-Output "FAILED: $script:stage. $script:failureDetail"
    if ($githubVerified) {
        Write-Output "Partial completion: GitHub was synced to $sha. Fix the failed stage and rerun this entry; pushes are non-forced."
    } else {
        Write-Output 'Deployment was not attempted. Fix the failed stage and rerun this entry.'
    }
    exit 1
}
