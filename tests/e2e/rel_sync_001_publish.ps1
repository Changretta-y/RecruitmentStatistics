param([switch]$FixtureOnly)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$entry = Join-Path $projectRoot 'scripts/publish-release.ps1'
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$gitExe = (Get-Command git.exe -ErrorAction Stop).Source
$tempParent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$taskRoot = Join-Path $tempParent ('job-rel-sync-001-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskRoot | Out-Null
$savedEnvironment = @{}
foreach ($key in @('GIT_ALLOW_PROTOCOL', 'GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL', 'GIT_TERMINAL_PROMPT')) {
    $savedEnvironment[$key] = [Environment]::GetEnvironmentVariable($key)
}
$env:GIT_ALLOW_PROTOCOL = 'file'
$env:GIT_CONFIG_NOSYSTEM = '1'
$env:GIT_CONFIG_GLOBAL = Join-Path $taskRoot 'empty.gitconfig'
$env:GIT_TERMINAL_PROMPT = '0'
[IO.File]::WriteAllText($env:GIT_CONFIG_GLOBAL, '')
$script:passed = 0
$script:failed = 0

function Git([string]$Repo, [string[]]$Arguments) {
    $output = & $gitExe -C $Repo @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Fixture Git command failed: $($Arguments -join ' '): $output" }
    return (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
}
function Assert([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}
function Ref([string]$Repo, [string]$Name = 'release') {
    return Git $Repo @('rev-parse', "refs/heads/$Name")
}
function ShellQuote([string]$Value) {
    return "'" + $Value.Replace("'", "'\''") + "'"
}
function WriteHook([string]$Repo, [string]$Name, [string]$Body) {
    [IO.File]::WriteAllText((Join-Path $Repo "hooks/$Name"), "#!/bin/sh`n$Body`n", [Text.UTF8Encoding]::new($false))
}
function Fixture([string]$Name) {
    $root = Join-Path $taskRoot $Name
    New-Item -ItemType Directory -Path $root | Out-Null
    $f = @{ Root = $root; Source = (Join-Path $root 'source'); Github = (Join-Path $root 'github.git'); Deploy = (Join-Path $root 'deploy.git'); Third = (Join-Path $root 'third.git'); Log = (Join-Path $root 'receive.log') }
    foreach ($repo in @($f.Github, $f.Deploy, $f.Third)) { Git $root @('init', '--bare', $repo) | Out-Null }
    Git $root @('init', '-b', 'release', $f.Source) | Out-Null
    Git $f.Source @('config', 'user.name', 'Release contract fixture') | Out-Null
    Git $f.Source @('config', 'user.email', 'fixture@example.invalid') | Out-Null
    [IO.File]::WriteAllText((Join-Path $f.Source 'payload.txt'), 'base')
    Git $f.Source @('add', 'payload.txt') | Out-Null
    Git $f.Source @('commit', '-m', 'fixture base') | Out-Null
    $f.Base = Git $f.Source @('rev-parse', 'HEAD')
    foreach ($repo in @($f.Github, $f.Deploy, $f.Third)) { Git $f.Source @('push', $repo, 'HEAD:refs/heads/release', 'HEAD:refs/heads/stable') | Out-Null }
    [IO.File]::WriteAllText((Join-Path $f.Source 'payload.txt'), 'target')
    Git $f.Source @('commit', '-am', 'fixture target') | Out-Null
    $f.Target = Git $f.Source @('rev-parse', 'HEAD')
    Git $f.Source @('remote', 'add', 'origin', $f.Github) | Out-Null
    Git $f.Source @('remote', 'add', 'deploy', $f.Deploy) | Out-Null
    foreach ($pair in @(@('github', $f.Github), @('deploy', $f.Deploy), @('third', $f.Third))) {
        $log = ShellQuote ($f.Log.Replace('\', '/'))
        WriteHook $pair[1] 'post-receive' ('while read old new ref; do printf ''{0} %s %s\n'' "$new" "$ref" >> {1}; done' -f $pair[0], $log)
    }
    return $f
}
function Publish($f, [string[]]$Arguments = @()) {
    $scripts = Join-Path $f.Source 'scripts'
    New-Item -ItemType Directory -Path $scripts -Force | Out-Null
    # The entry is copied as an opaque executable; its contents are never read.
    Copy-Item -LiteralPath $entry -Destination (Join-Path $scripts 'publish-release.ps1')
    Push-Location $f.Source
    try {
        $output = & $pwsh -NoProfile -File (Join-Path $scripts 'publish-release.ps1') @Arguments 2>&1
        return @{ Code = $LASTEXITCODE; Output = (($output | ForEach-Object { $_.ToString() }) -join "`n") }
    } finally { Pop-Location }
}
function NoPublication($f, $result) {
    Assert ($result.Code -ne 0) 'Invalid invocation must return nonzero'
    Assert ((Ref $f.Github) -eq $f.Base) 'GitHub changed despite validation failure'
    Assert ((Ref $f.Deploy) -eq $f.Base) 'Deploy changed despite validation failure'
    Assert (-not (Test-Path -LiteralPath $f.Log)) 'Validation failure must occur before push'
}
function Case([string]$Name, [scriptblock]$Body) {
    try { & $Body; $script:passed++; Write-Host "PASS $Name" }
    catch { $script:failed++; Write-Host "FAIL $Name`: $($_.Exception.Message)" }
}

try {
    Case 'fixture: Git commits, file remotes, receive order, rejection and ls-remote' {
        $f = Fixture 'fixture'
        Git $f.Source @('push', $f.Github, "$($f.Target):refs/heads/release") | Out-Null
        Git $f.Source @('push', $f.Deploy, "$($f.Target):refs/heads/release") | Out-Null
        $lines = @(Get-Content -LiteralPath $f.Log)
        Assert ($lines.Count -eq 2 -and $lines[0].StartsWith('github ') -and $lines[1].StartsWith('deploy ')) 'Receive hooks do not expose ordering'
        Assert ((Git $f.Source @('ls-remote', $f.Github, 'refs/heads/release')).StartsWith($f.Target)) 'ls-remote fixture mismatch'
        WriteHook $f.Third 'pre-receive' 'echo fixture-rejection >&2; exit 1'
        $rejected = & $gitExe -C $f.Source push $f.Third "$($f.Target):refs/heads/release" 2>&1
        Assert ($LASTEXITCODE -ne 0) 'Reject hook not effective'
        Assert ((Ref $f.Third) -eq $f.Base) 'Rejected push changed fixture ref'
        WriteHook $f.Github 'post-receive' "git update-ref refs/heads/release $($f.Base)"
        Git $f.Source @('push', $f.Github, "$($f.Base):refs/heads/fixture-proof") | Out-Null
        Assert ((Ref $f.Github) -eq $f.Base) 'Post-receive readback-mismatch fixture not effective'
        Assert ((Git $f.Source @('ls-remote', $f.Github, 'refs/heads/release')).StartsWith($f.Base)) 'Post-receive change is not visible to ls-remote'
        $version = & $pwsh -NoProfile -Command '$PSVersionTable.PSVersion.ToString()'
        Assert ($LASTEXITCODE -eq 0 -and $version) 'PowerShell child process unavailable'
    }
    if ($script:failed -gt 0) { throw 'Fixture validation failed; no product RED may be claimed' }
    if (-not $FixtureOnly) {
        Case 'public release entry exists' { Assert (Test-Path -LiteralPath $entry -PathType Leaf) 'Missing public scripts/publish-release.ps1 entry (required behavior absent)' }
        if (Test-Path -LiteralPath $entry -PathType Leaf) {
            Case 'same captured SHA, GitHub first, dirty files and unrelated refs preserved' {
                $f = Fixture 'success'
                [IO.File]::WriteAllText((Join-Path $f.Source 'payload.txt'), 'uncommitted tracked content')
                [IO.File]::WriteAllText((Join-Path $f.Source 'untracked.txt'), 'uncommitted untracked content')
                $r = Publish $f
                Assert ($r.Code -eq 0) "Publication failed: $($r.Output)"
                Assert ((Ref $f.Github) -eq $f.Target -and (Ref $f.Deploy) -eq $f.Target) 'Both release refs must match captured SHA'
                $lines = @(Get-Content -LiteralPath $f.Log)
                Assert ($lines.Count -eq 2 -and $lines[0] -eq "github $($f.Target) refs/heads/release" -and $lines[1] -eq "deploy $($f.Target) refs/heads/release") 'Receive order or SHA mismatch'
                Assert ((Ref $f.Github 'stable') -eq $f.Base -and (Ref $f.Deploy 'stable') -eq $f.Base) 'Unrelated refs changed'
                Assert ([IO.File]::ReadAllText((Join-Path $f.Source 'payload.txt')) -eq 'uncommitted tracked content') 'Tracked dirty content changed'
                Assert ([IO.File]::ReadAllText((Join-Path $f.Source 'untracked.txt')) -eq 'uncommitted untracked content') 'Untracked content changed'
                Assert ((Git $f.Source @('rev-parse', 'HEAD')) -eq $f.Target) 'Script committed dirty files or moved HEAD'
                Assert ($r.Output.Contains($f.Target) -and $r.Output -match '(?i)github' -and $r.Output -match '(?i)deploy|部署') 'Output must identify captured SHA and both stages'
            }
            Case 'origin multiple push URLs ignored and preserved' {
                $f = Fixture 'pushurls'
                Git $f.Source @('config', '--add', 'remote.origin.pushurl', $f.Third) | Out-Null
                Git $f.Source @('config', '--add', 'remote.origin.pushurl', $f.Deploy) | Out-Null
                $before = Git $f.Source @('config', '--get-all', 'remote.origin.pushurl')
                $r = Publish $f
                Assert ($r.Code -eq 0 -and (Ref $f.Github) -eq $f.Target -and (Ref $f.Deploy) -eq $f.Target) 'Explicit fetch URL publication failed'
                Assert ((Ref $f.Third) -eq $f.Base) 'Third pushurl destination was updated'
                Assert ((Git $f.Source @('config', '--get-all', 'remote.origin.pushurl')) -eq $before) 'pushurl configuration changed'
                $lines = @(Get-Content -LiteralPath $f.Log)
                Assert ($lines.Count -eq 2 -and $lines[0].StartsWith('github ') -and $lines[1].StartsWith('deploy ')) 'Dual pushurl bypassed publication order'
            }
            Case 'custom remote names' {
                $f = Fixture 'custom'
                Git $f.Source @('remote', 'rename', 'origin', 'code-store') | Out-Null
                Git $f.Source @('remote', 'rename', 'deploy', 'server-store') | Out-Null
                $r = Publish $f @('-GitHubRemote', 'code-store', '-DeployRemote', 'server-store')
                Assert ($r.Code -eq 0 -and (Ref $f.Github) -eq $f.Target -and (Ref $f.Deploy) -eq $f.Target) 'Custom remote parameters failed'
            }
            Case 'GitHub rejection blocks deployment' {
                $f = Fixture 'github-reject'
                WriteHook $f.Github 'pre-receive' 'echo fixture-github-rejection >&2; exit 1'
                $r = Publish $f
                NoPublication $f $r
                Assert ($r.Output -match '(?i)github|origin') 'Failure output does not identify GitHub stage'
            }
            Case 'GitHub non-fast-forward is never forced' {
                $f = Fixture 'github-diverged'
                Git $f.Source @('checkout', '-b', 'diverged', $f.Base) | Out-Null
                [IO.File]::WriteAllText((Join-Path $f.Source 'diverged.txt'), 'remote independent history')
                Git $f.Source @('add', 'diverged.txt') | Out-Null
                Git $f.Source @('commit', '-m', 'remote divergence') | Out-Null
                $diverged = Git $f.Source @('rev-parse', 'HEAD')
                Git $f.Source @('push', $f.Github, 'HEAD:refs/heads/release') | Out-Null
                Remove-Item -LiteralPath $f.Log
                Git $f.Source @('checkout', 'release') | Out-Null
                $r = Publish $f
                Assert ($r.Code -ne 0 -and (Ref $f.Github) -eq $diverged -and (Ref $f.Deploy) -eq $f.Base) 'Non-fast-forward was forced or deployment was attempted'
                Assert (-not (Test-Path -LiteralPath $f.Log)) 'Failed GitHub push must not reach deployment'
            }
            Case 'GitHub post-push verification mismatch blocks deployment' {
                $f = Fixture 'github-verification'
                WriteHook $f.Github 'post-receive' "git update-ref refs/heads/release $($f.Base)"
                $r = Publish $f
                Assert ($r.Code -ne 0 -and (Ref $f.Github) -eq $f.Base -and (Ref $f.Deploy) -eq $f.Base) 'GitHub verification mismatch did not block deployment'
                Assert (-not (Test-Path -LiteralPath $f.Log)) 'Deployment receive observed after GitHub verification failure'
            }
            Case 'deployment non-fast-forward is never forced' {
                $f = Fixture 'deploy-diverged'
                Git $f.Source @('checkout', '-b', 'diverged', $f.Base) | Out-Null
                [IO.File]::WriteAllText((Join-Path $f.Source 'diverged.txt'), 'deployment independent history')
                Git $f.Source @('add', 'diverged.txt') | Out-Null
                Git $f.Source @('commit', '-m', 'deployment divergence') | Out-Null
                $diverged = Git $f.Source @('rev-parse', 'HEAD')
                Git $f.Source @('push', $f.Deploy, 'HEAD:refs/heads/release') | Out-Null
                Remove-Item -LiteralPath $f.Log
                Git $f.Source @('checkout', 'release') | Out-Null
                $r = Publish $f
                Assert ($r.Code -ne 0 -and (Ref $f.Github) -eq $f.Target -and (Ref $f.Deploy) -eq $diverged) 'Deployment non-fast-forward was forced or partial state incorrect'
            }
            Case 'deployment rejection reports partial completion, rerun recovers' {
                $f = Fixture 'deploy-reject'
                WriteHook $f.Deploy 'pre-receive' 'echo fixture-deploy-rejection >&2; exit 1'
                $r = Publish $f
                Assert ($r.Code -ne 0 -and (Ref $f.Github) -eq $f.Target -and (Ref $f.Deploy) -eq $f.Base) 'Partial completion state incorrect'
                Assert ($r.Output.Contains($f.Target) -and $r.Output -match '(?i)github' -and $r.Output -match '(?i)deploy|部署' -and $r.Output -match '(?i)rerun|retry|again|重跑|重新') 'Partial completion output must explain rerun'
                Remove-Item -LiteralPath (Join-Path $f.Deploy 'hooks/pre-receive')
                $retry = Publish $f
                Assert ($retry.Code -eq 0 -and (Ref $f.Github) -eq $f.Target -and (Ref $f.Deploy) -eq $f.Target) 'Rerun failed to synchronize both refs'
            }
            Case 'deployment verification mismatch returns nonzero' {
                $f = Fixture 'deploy-verification'
                WriteHook $f.Deploy 'post-receive' "git update-ref refs/heads/release $($f.Base)"
                $r = Publish $f
                Assert ($r.Code -ne 0 -and (Ref $f.Github) -eq $f.Target -and (Ref $f.Deploy) -eq $f.Base) 'Deployment mismatch must be a failed partial release'
            }
            Case 'DryRun reports SHA and ordered plan without pushes' {
                $f = Fixture 'dryrun'
                $r = Publish $f @('-DryRun')
                Assert ($r.Code -eq 0 -and (Ref $f.Github) -eq $f.Base -and (Ref $f.Deploy) -eq $f.Base) 'DryRun changed refs or failed'
                Assert (-not (Test-Path -LiteralPath $f.Log)) 'DryRun invoked receive hooks'
                Assert ($r.Output.Contains($f.Target) -and $r.Output -match '(?is)github.*(?:deploy|部署)') 'DryRun must show SHA and GitHub-before-deploy plan'
            }
            foreach ($mode in @('non-release', 'detached', 'missing-github', 'missing-deploy', 'multiple-github-fetch', 'multiple-deploy-fetch', 'same-destination')) {
                Case "validation before any push: $mode" {
                    $f = Fixture $mode
                    switch ($mode) {
                        'non-release' { Git $f.Source @('checkout', '-b', 'feature') | Out-Null }
                        'detached' { Git $f.Source @('checkout', '--detach', $f.Target) | Out-Null }
                        'missing-github' { Git $f.Source @('remote', 'remove', 'origin') | Out-Null }
                        'missing-deploy' { Git $f.Source @('remote', 'remove', 'deploy') | Out-Null }
                        'multiple-github-fetch' { Git $f.Source @('config', '--add', 'remote.origin.url', $f.Third) | Out-Null }
                        'multiple-deploy-fetch' { Git $f.Source @('config', '--add', 'remote.deploy.url', $f.Third) | Out-Null }
                        'same-destination' { Git $f.Source @('remote', 'set-url', 'deploy', $f.Github) | Out-Null }
                    }
                    NoPublication $f (Publish $f)
                }
            }
        }
    }
    Write-Host "RESULT passed=$script:passed failed=$script:failed fixtureOnly=$FixtureOnly"
} finally {
    foreach ($key in $savedEnvironment.Keys) { [Environment]::SetEnvironmentVariable($key, $savedEnvironment[$key]) }
    $resolvedRoot = [IO.Path]::GetFullPath($taskRoot)
    $expectedParent = [IO.Path]::GetFullPath($tempParent).TrimEnd('\', '/')
    Assert ((Split-Path -Parent $resolvedRoot).TrimEnd('\', '/') -eq $expectedParent -and (Split-Path -Leaf $resolvedRoot) -match '^job-rel-sync-001-[a-f0-9]{32}$') 'Refusing cleanup outside exact task temporary root'
    Remove-Item -LiteralPath $resolvedRoot -Recurse -Force
}
if ($script:failed -gt 0) { exit 1 }
