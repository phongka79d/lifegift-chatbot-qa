#Requires -Version 5.1
<#
.SYNOPSIS
    Orchestrate OpenSpec implementation through Herdr-managed coding agents.

.DESCRIPTION
    Windows/PowerShell state machine for Herdr:

      Preflight
        -> Discover agents/panes
        -> Select implementation agent
        -> Dispatch implementation task
        -> Wait/poll agent
        -> Run reviewer agent
        -> Collect findings
        -> Dispatch focused repairs
        -> Re-run validation
        -> Check OpenSpec task status
        -> Repeat until all tasks complete
        -> Final report

    All agent control goes through `herdr`. The script never launches
    commandcode, agy, codex, or any other agent executable. Bare `herdr`
    is refused because it can open the TUI.

    Agent IDs, pane IDs, tab IDs, and workspace IDs are read from Herdr
    JSON. The script never invents those handles.

    Idle or done alone is not completion. Completion requires a settled
    lifecycle plus a structured report plus OpenSpec checkbox evidence
    plus a validation result.

.PARAMETER ChangeName
    OpenSpec change folder name, for example implement-lifegift-chatbot.

.PARAMETER WorkspaceId
    Optional live Herdr workspace ID (example: w3). When set, both the
    implementer and reviewer must occupy that workspace.

.PARAMETER Implementer
    Live agent name or pane ID. Kind labels such as codex are accepted
    only when exactly one live agent of that kind exists.

.PARAMETER Reviewer
    Live agent name or pane ID. Must resolve to a different pane than
    the implementer.

.PARAMETER PollSeconds
    Settled-state wait chunk. Default 180. The script prefers
    `herdr agent wait` / `herdr agent prompt --wait` over busy polling.

.PARAMETER MaxReviewCycles
    Maximum review/repair loops per task. Default 10.

.PARAMETER TimeoutSeconds
    Wall-clock budget for one implement, review, or repair wait.
    Default 1800.

.PARAMETER DryRun
    Run preflight, discovery, and selection. Print planned prompts.
    Do not submit work, send keys, split, or close panes.

.PARAMETER Resume
    Continue the in-progress run stored under .herdr/orchestrator.

.PARAMETER SmokeTest
    Run one read-only implement then review cycle even when OpenSpec
    has no remaining tasks. Agents must not edit files or checkboxes.

.PARAMETER WhatIf
    Show mutating Herdr calls without executing them.

.EXAMPLE
    .\scripts\herdr-orchestrator.ps1 -ChangeName implement-lifegift-chatbot -Implementer commandcode -Reviewer w3:p1 -DryRun

.EXAMPLE
    .\scripts\herdr-orchestrator.ps1 -ChangeName implement-lifegift-chatbot -Implementer commandcode -Reviewer w3:p1 -Resume
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]*$')]
    [string]$ChangeName,

    [string]$WorkspaceId,

    [string]$Implementer,

    [string]$Reviewer,

    [ValidateRange(5, 86400)]
    [int]$PollSeconds = 180,

    [ValidateRange(1, 100)]
    [int]$MaxReviewCycles = 10,

    [ValidateRange(30, 86400)]
    [int]$TimeoutSeconds = 1800,

    [switch]$DryRun,

    [switch]$Resume,

    [switch]$SmokeTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($TimeoutSeconds -lt $PollSeconds) {
    throw "TimeoutSeconds ($TimeoutSeconds) must be greater than or equal to PollSeconds ($PollSeconds)."
}

$script:RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$script:StateRoot = Join-Path (Join-Path $script:RepoRoot '.herdr') (Join-Path 'orchestrator' $ChangeName)
$script:StatePath = Join-Path $script:StateRoot 'state.json'
$script:EventPath = Join-Path $script:StateRoot 'events.jsonl'
$script:TranscriptDir = Join-Path $script:StateRoot 'transcripts'
$script:ReportDir = Join-Path $script:StateRoot 'reports'
$script:State = $null
$script:Caller = $null
$script:MutationsAllowed = -not ($DryRun.IsPresent -or $WhatIfPreference)
$script:SmokeTest = [bool]$SmokeTest.IsPresent
$script:ForbiddenAgentExecutables = @(
    'commandcode', 'agy', 'codex', 'claude', 'gemini', 'cursor', 'devin',
    'opencode', 'copilot', 'kimi', 'kiro', 'droid', 'amp', 'grok', 'hermes'
)

# ---------------------------------------------------------------------------
# Output and errors
# ---------------------------------------------------------------------------

function Write-OrchLog {
    param(
        [Parameter(Mandatory = $true)][string]$Level,
        [Parameter(Mandatory = $true)][string]$Message
    )
    $stamp = (Get-Date).ToUniversalTime().ToString('o')
    Write-Host ("[{0}] [{1}] {2}" -f $stamp, $Level, $Message)
}

function New-OrchError {
    param(
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Message,
        [string]$Evidence,
        [string]$Next
    )
    $lines = @(
        'BLOCKER',
        ("code: {0}" -f $Code),
        ("message: {0}" -f $Message)
    )
    if ($Evidence) { $lines += ("evidence: {0}" -f $Evidence) }
    if ($Next) { $lines += ("next: {0}" -f $Next) }
    $text = $lines -join [Environment]::NewLine
    $ex = New-Object System.Exception $text
    $ex.Data['blocker_code'] = $Code
    return $ex
}

function Stop-Orch {
    param(
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Message,
        [string]$Evidence,
        [string]$Next
    )
    $ex = New-OrchError -Code $Code -Message $Message -Evidence $Evidence -Next $Next
    if ($script:State) {
        $script:State.phase = 'Blocked'
        $script:State.blocker = @{
            code      = $Code
            message   = $Message
            evidence  = $Evidence
            next      = $Next
            at        = (Get-Date).ToUniversalTime().ToString('o')
        }
        Save-OrchState
        Write-OrchEvent -Name 'blocked' -From $script:State.phase -To 'Blocked' -Reason $Message -BlockerCode $Code
    }
    Write-OrchLog -Level 'BLOCKER' -Message $ex.Message
    throw $ex
}

# ---------------------------------------------------------------------------
# Filesystem / JSON helpers
# ---------------------------------------------------------------------------

function Write-JsonAtomic {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)]$Object
    )
    $dir = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $tmp = "$Path.tmp"
    $json = $Object | ConvertTo-Json -Depth 30
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($tmp, $json, $utf8)
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}

function Test-PathUnderRoot {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Root
    )
    $full = [System.IO.Path]::GetFullPath($Path)
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\', '/') + '\'
    $probe = $full.TrimEnd('\', '/') + '\'
    return $probe.ToLowerInvariant().StartsWith($rootFull.ToLowerInvariant())
}

function Get-NormalizedPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/').ToLowerInvariant()
}

function Test-SafeRepoPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-PathUnderRoot -Path $Path -Root $script:RepoRoot)) {
        Stop-Orch -Code 'UNSAFE_PATH' -Message "Refusing path outside the repository." -Evidence $Path -Next "Use a path under $script:RepoRoot."
    }
    return [System.IO.Path]::GetFullPath($Path)
}

function Get-PropertyValue {
    param($Object, [string]$Name, $Default = $null)
    if ($null -eq $Object) { return $Default }
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -eq $prop) { return $Default }
    return $prop.Value
}

# ---------------------------------------------------------------------------
# Herdr invocation
# ---------------------------------------------------------------------------

function Test-HerdrArgv {
    param([string[]]$HerdrArgs)
    if (-not $HerdrArgs -or $HerdrArgs.Count -eq 0) {
        Stop-Orch -Code 'HERDR_BARE_REFUSED' -Message "Refusing to run bare herdr because it can open the TUI." -Next "Call a subcommand such as herdr status --json."
    }
    $joined = ($HerdrArgs -join ' ').ToLowerInvariant()
    if ($HerdrArgs[0] -eq 'server' -and $HerdrArgs -contains 'stop') {
        Stop-Orch -Code 'UNSAFE_OPERATION' -Message "Refusing herdr server stop from the orchestrator."
    }
    foreach ($exe in $script:ForbiddenAgentExecutables) {
        if ($HerdrArgs[0] -eq $exe) {
            Stop-Orch -Code 'UNSAFE_OPERATION' -Message "Refusing to invoke $exe directly. All agent control must go through Herdr."
        }
    }
    return $joined
}

function Invoke-Herdr {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
        [string[]]$HerdrArgs,

        [switch]$AllowFailure
    )

    Test-HerdrArgv -HerdrArgs $HerdrArgs | Out-Null

    $herdr = Get-Command herdr -ErrorAction SilentlyContinue
    if (-not $herdr) {
        Stop-Orch -Code 'HERDR_CLI_MISSING' -Message "herdr is not on PATH." -Next "Run this script from a Herdr-managed pane so the session CLI is available."
    }

    Write-OrchLog -Level 'HERDR' -Message ("herdr {0}" -f ($HerdrArgs -join ' '))

    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $raw = & herdr @HerdrArgs 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $oldEap

    $chunks = New-Object System.Collections.Generic.List[string]
    foreach ($item in @($raw)) {
        if ($item -is [System.Management.Automation.ErrorRecord]) {
            $chunks.Add($item.ToString()) | Out-Null
        }
        else {
            $chunks.Add([string]$item) | Out-Null
        }
    }
    $text = ($chunks -join [Environment]::NewLine).Trim()

    $parsed = $null
    if ($text) {
        $start = $text.IndexOf('{')
        $end = $text.LastIndexOf('}')
        if ($start -ge 0 -and $end -gt $start) {
            $jsonText = $text.Substring($start, $end - $start + 1)
            try {
                $parsed = $jsonText | ConvertFrom-Json
            }
            catch {
                if (-not $AllowFailure) {
                    $preview = $text
                    if ($preview.Length -gt 800) { $preview = $preview.Substring(0, 800) + '...' }
                    Stop-Orch -Code 'HERDR_JSON_INVALID' -Message "Herdr output was not valid JSON." -Evidence $preview
                }
            }
        }
        elseif (-not $AllowFailure) {
            $preview = $text
            if ($preview.Length -gt 800) { $preview = $preview.Substring(0, 800) + '...' }
            Stop-Orch -Code 'HERDR_JSON_INVALID' -Message "Herdr output was not valid JSON." -Evidence $preview
        }
    }

    $errorCode = $null
    $errorMessage = $null
    if ($parsed -and $parsed.PSObject.Properties['error']) {
        $errorCode = Get-PropertyValue $parsed.error 'code'
        $errorMessage = Get-PropertyValue $parsed.error 'message'
    }

    $ok = ($code -eq 0 -and -not $errorCode)
    if (-not $ok -and -not $AllowFailure) {
        $detail = $errorMessage
        if (-not $detail) { $detail = $text }
        if (-not $detail) { $detail = "herdr exited with code $code" }
        Stop-Orch -Code $(if ($errorCode) { $errorCode } else { 'HERDR_COMMAND_FAILED' }) -Message $detail -Evidence ("herdr {0}" -f ($HerdrArgs -join ' '))
    }

    return [pscustomobject]@{
        Ok           = [bool]$ok
        ExitCode     = $code
        Text         = $text
        Json         = $parsed
        Result       = $(if ($parsed) { Get-PropertyValue $parsed 'result' } else { $null })
        ErrorCode    = $errorCode
        ErrorMessage = $errorMessage
    }
}

function Invoke-HerdrReadOnly {
    param([Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)][string[]]$HerdrArgs)
    return Invoke-Herdr @HerdrArgs
}

function Invoke-HerdrMutation {
    param(
        [Parameter(Mandatory = $true)][string]$Target,
        [Parameter(Mandatory = $true)][string]$Action,
        [Parameter(Mandatory = $true)][string[]]$HerdrArgs
    )
    if (-not $script:MutationsAllowed) {
        Write-OrchLog -Level 'DRYRUN' -Message ("skip {0} on {1}: herdr {2}" -f $Action, $Target, ($HerdrArgs -join ' '))
        return [pscustomobject]@{
            Ok           = $true
            ExitCode     = 0
            Text         = ''
            Json         = $null
            Result       = $null
            ErrorCode    = $null
            ErrorMessage = $null
            Skipped      = $true
        }
    }
    if ($PSCmdlet.ShouldProcess($Target, $Action)) {
        return Invoke-Herdr @HerdrArgs -AllowFailure
    }
    return [pscustomobject]@{
        Ok           = $true
        ExitCode     = 0
        Text         = ''
        Json         = $null
        Result       = $null
        ErrorCode    = $null
        ErrorMessage = $null
        Skipped      = $true
    }
}

# ---------------------------------------------------------------------------
# OpenSpec
# ---------------------------------------------------------------------------

function Invoke-OpenSpecJson {
    param([Parameter(Mandatory = $true)][string[]]$SpecArgs)

    $openspec = Get-Command openspec -ErrorAction SilentlyContinue
    if (-not $openspec) {
        return $null
    }

    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $raw = & openspec @SpecArgs 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $oldEap

    $chunks = New-Object System.Collections.Generic.List[string]
    foreach ($item in @($raw)) {
        if ($item -is [System.Management.Automation.ErrorRecord]) {
            $chunks.Add($item.ToString()) | Out-Null
        }
        else {
            $chunks.Add([string]$item) | Out-Null
        }
    }
    $text = ($chunks -join [Environment]::NewLine).Trim()
    if ($code -ne 0) {
        Stop-Orch -Code 'OPENSPEC_COMMAND_FAILED' -Message "openspec $($SpecArgs -join ' ') failed." -Evidence $text
    }
    $start = $text.IndexOf('{')
    $end = $text.LastIndexOf('}')
    if ($start -lt 0 -or $end -le $start) {
        Stop-Orch -Code 'OPENSPEC_JSON_INVALID' -Message "openspec did not return JSON." -Evidence $text
    }
    return ($text.Substring($start, $end - $start + 1) | ConvertFrom-Json)
}

function Get-OpenSpecTasksFromMarkdown {
    param([Parameter(Mandatory = $true)][string]$TasksPath)
    $safe = Test-SafeRepoPath -Path $TasksPath
    $lines = Get-Content -LiteralPath $safe
    $tasks = New-Object System.Collections.Generic.List[object]
    $index = 0
    foreach ($line in $lines) {
        if ($line -match '^- \[([ xX])\]\s+(.+)$') {
            $index++
            $desc = $Matches[2].Trim()
            $idFromText = $null
            if ($desc -match '^(\d+\.\d+)\b') { $idFromText = $Matches[1] }
            $tasks.Add([pscustomobject]@{
                    id          = $(if ($idFromText) { $idFromText } else { [string]$index })
                    description = $desc
                    done        = ($Matches[1] -match '[xX]')
                }) | Out-Null
        }
    }
    return $tasks.ToArray()
}

function Get-OpenSpecSnapshot {
    $changeDir = Join-Path (Join-Path $script:RepoRoot 'openspec') (Join-Path 'changes' $ChangeName)
    $tasksPath = Join-Path $changeDir 'tasks.md'
    if (-not (Test-Path -LiteralPath $changeDir)) {
        Stop-Orch -Code 'OPENSPEC_CHANGE_MISSING' -Message "OpenSpec change '$ChangeName' was not found." -Evidence $changeDir -Next "Pass an existing change from openspec list --json."
    }

    $apply = Invoke-OpenSpecJson -SpecArgs @('instructions', 'apply', '--change', $ChangeName, '--json')
    $status = Invoke-OpenSpecJson -SpecArgs @('status', '--change', $ChangeName, '--json')

    $tasks = @()
    $contextFiles = @()
    $progress = $null
    $applyState = $null
    $allowedRoots = @($script:RepoRoot)

    if ($apply) {
        $tasks = @($apply.tasks)
        $progress = $apply.progress
        $applyState = $apply.state
        if ($apply.contextFiles) {
            foreach ($group in $apply.contextFiles.PSObject.Properties) {
                foreach ($path in @($group.Value)) { $contextFiles += [string]$path }
            }
        }
    }
    elseif (Test-Path -LiteralPath $tasksPath) {
        $tasks = @(Get-OpenSpecTasksFromMarkdown -TasksPath $tasksPath)
        $done = @($tasks | Where-Object { $_.done }).Count
        $progress = [pscustomobject]@{ total = $tasks.Count; complete = $done; remaining = ($tasks.Count - $done) }
        $applyState = $(if ($progress.remaining -eq 0 -and $progress.total -gt 0) { 'all_done' } else { 'ready' })
        $contextFiles = @(
            (Join-Path $changeDir 'proposal.md'),
            (Join-Path $changeDir 'design.md'),
            $tasksPath
        )
        $specRoot = Join-Path $changeDir 'specs'
        if (Test-Path -LiteralPath $specRoot) {
            $contextFiles += Get-ChildItem -LiteralPath $specRoot -Recurse -Filter '*.md' | ForEach-Object { $_.FullName }
        }
        Write-OrchLog -Level 'WARN' -Message "openspec CLI not found; parsed tasks.md directly."
    }
    else {
        Stop-Orch -Code 'OPENSPEC_TASKS_MISSING' -Message "Neither openspec CLI nor tasks.md is available." -Evidence $tasksPath
    }

    if ($status -and $status.actionContext -and $status.actionContext.allowedEditRoots) {
        $allowedRoots = @($status.actionContext.allowedEditRoots)
    }

    $pending = @($tasks | Where-Object { -not $_.done })
    return [pscustomobject]@{
        ChangeDir     = $changeDir
        TasksPath     = $tasksPath
        Status        = $status
        Apply         = $apply
        Tasks         = $tasks
        Pending       = $pending
        Progress      = $progress
        ApplyState    = $applyState
        ContextFiles  = $contextFiles
        AllowedRoots  = $allowedRoots
        PlanningHome  = $(if ($status) { Get-PropertyValue $status 'planningHome' } else { $null })
    }
}

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

function New-OrchState {
    param($Snapshot)
    $runId = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') + '-' + ([guid]::NewGuid().ToString('N').Substring(0, 8))
    return [pscustomobject]@{
        schema_version   = 1
        protocol         = 'herdr-orchestrator/v1'
        run_id           = $runId
        change_name      = $ChangeName
        repo_root        = $script:RepoRoot
        created_at       = (Get-Date).ToUniversalTime().ToString('o')
        updated_at       = (Get-Date).ToUniversalTime().ToString('o')
        phase            = 'Preflight'
        caller           = $null
        workspace_filter = $WorkspaceId
        implementer      = $null
        reviewer         = $null
        created_pane_ids = @()
        current_task     = $null
        review_cycle     = 0
        last_dispatch    = $null
        last_wait        = $null
        last_findings    = @()
        last_validation  = $null
        completed_task_ids = @()
        history          = @()
        blocker          = $null
        options          = @{
            poll_seconds      = $PollSeconds
            max_review_cycles = $MaxReviewCycles
            timeout_seconds   = $TimeoutSeconds
            dry_run           = [bool]$DryRun
            smoke_test        = [bool]$script:SmokeTest
        }
        openspec         = @{
            apply_state = $Snapshot.ApplyState
            complete    = $Snapshot.Progress.complete
            total       = $Snapshot.Progress.total
            remaining   = $Snapshot.Progress.remaining
        }
        git_snapshot     = @()
    }
}

function Save-OrchState {
    if (-not $script:State) { return }
    $script:State.updated_at = (Get-Date).ToUniversalTime().ToString('o')
    Write-JsonAtomic -Path $script:StatePath -Object $script:State
}

function Write-OrchEvent {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string]$From,
        [string]$To,
        [string]$Reason,
        [string]$BlockerCode,
        [string[]]$Evidence
    )
    $dir = Split-Path -Parent $script:EventPath
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $event = [ordered]@{
        at           = (Get-Date).ToUniversalTime().ToString('o')
        actor        = 'herdr-orchestrator'
        event        = $Name
        change_name  = $ChangeName
        run_id       = $(if ($script:State) { $script:State.run_id } else { $null })
        phase        = $(if ($script:State) { $script:State.phase } else { $null })
        task_id      = $(if ($script:State -and $script:State.current_task) { Get-PropertyValue $script:State.current_task 'id' } else { $null })
        from         = $From
        to           = $To
        reason       = $Reason
        blocker_code = $BlockerCode
        evidence     = $Evidence
    }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::AppendAllText($script:EventPath, (($event | ConvertTo-Json -Depth 10 -Compress) + [Environment]::NewLine), $utf8)
}

function Set-OrchPhase {
    param([Parameter(Mandatory = $true)][string]$Phase, [string]$Reason)
    $from = $script:State.phase
    $script:State.phase = $Phase
    $entry = [pscustomobject]@{
        at     = (Get-Date).ToUniversalTime().ToString('o')
        from   = $from
        to     = $Phase
        reason = $Reason
    }
    $history = @()
    if ($script:State.history) { $history = @($script:State.history) }
    $script:State.history = $history + $entry
    Save-OrchState
    Write-OrchEvent -Name 'phase' -From $from -To $Phase -Reason $Reason
    Write-OrchLog -Level 'STATE' -Message ("{0} -> {1}: {2}" -f $from, $Phase, $Reason)
}

function Import-OrchState {
    if (-not (Test-Path -LiteralPath $script:StatePath)) {
        Stop-Orch -Code 'RESUME_STATE_MISSING' -Message "No orchestrator state exists for change '$ChangeName'." -Evidence $script:StatePath -Next "Run without -Resume to start a new run."
    }
    $loaded = Get-Content -LiteralPath $script:StatePath -Raw | ConvertFrom-Json
    if ($loaded.change_name -ne $ChangeName) {
        Stop-Orch -Code 'INCONSISTENT_STATE' -Message "State change_name '$($loaded.change_name)' does not match -ChangeName '$ChangeName'." -Evidence $script:StatePath
    }
    if ($loaded.repo_root -and (Get-NormalizedPath $loaded.repo_root) -ne (Get-NormalizedPath $script:RepoRoot)) {
        Stop-Orch -Code 'INCONSISTENT_STATE' -Message "State repo_root does not match this repository." -Evidence $loaded.repo_root
    }
    return $loaded
}

# ---------------------------------------------------------------------------
# Preflight / discovery
# ---------------------------------------------------------------------------

function Get-GitSnapshot {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) { return @() }
    $old = Get-Location
    try {
        Set-Location $script:RepoRoot
        $oldEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $text = & git status --short 2>&1
        $ErrorActionPreference = $oldEap
        return @($text | ForEach-Object { [string]$_ } | Where-Object { $_ })
    }
    finally {
        Set-Location $old
    }
}

function Assert-Preflight {
    if ($env:HERDR_ENV -ne '1') {
        Stop-Orch -Code 'HERDR_ENV_MISSING' -Message "This script is not running inside a Herdr-managed pane (HERDR_ENV is not 1)." -Evidence ("HERDR_ENV={0}" -f $env:HERDR_ENV) -Next "Start the orchestrator from a pane that Herdr injected. Do not control the session from outside Herdr."
    }
    if (-not $env:HERDR_WORKSPACE_ID -or -not $env:HERDR_TAB_ID -or -not $env:HERDR_PANE_ID) {
        Stop-Orch -Code 'HERDR_PANE_UNMANAGED' -Message "Herdr injected IDs are missing." -Evidence ("workspace={0}; tab={1}; pane={2}" -f $env:HERDR_WORKSPACE_ID, $env:HERDR_TAB_ID, $env:HERDR_PANE_ID) -Next "Run from a Herdr-managed pane so HERDR_WORKSPACE_ID, HERDR_TAB_ID, and HERDR_PANE_ID are set."
    }

    $status = Invoke-HerdrReadOnly status --json
    $server = Get-PropertyValue $status.Json 'server'
    if (-not $server -or -not (Get-PropertyValue $server 'running')) {
        Stop-Orch -Code 'HERDR_SERVER_DOWN' -Message "Herdr server is not running." -Evidence $status.Text -Next "Start Herdr and re-run from a managed pane."
    }

    $current = Invoke-HerdrReadOnly pane current --current
    $pane = Get-PropertyValue $current.Result 'pane'
    if (-not $pane) {
        Stop-Orch -Code 'HERDR_PANE_UNMANAGED' -Message "herdr pane current --current did not return a pane." -Evidence $current.Text
    }

    $script:Caller = [pscustomobject]@{
        workspace_id = [string]$pane.workspace_id
        tab_id       = [string]$pane.tab_id
        pane_id      = [string]$pane.pane_id
        agent        = [string](Get-PropertyValue $pane 'agent')
        name         = [string](Get-PropertyValue $pane 'name')
        cwd          = [string](Get-PropertyValue $pane 'cwd')
        status       = [string](Get-PropertyValue $pane 'agent_status')
    }

    if ($script:Caller.pane_id -ne $env:HERDR_PANE_ID) {
        Stop-Orch -Code 'INCONSISTENT_STATE' -Message "Caller pane ID from Herdr JSON does not match HERDR_PANE_ID." -Evidence ("json={0}; env={1}" -f $script:Caller.pane_id, $env:HERDR_PANE_ID)
    }

    $wsList = Invoke-HerdrReadOnly workspace list
    $workspaces = @($wsList.Result.workspaces)
    $liveWs = @($workspaces | ForEach-Object { [string]$_.workspace_id })
    if ($liveWs -notcontains $script:Caller.workspace_id) {
        Stop-Orch -Code 'WORKSPACE_INVALID' -Message "Caller workspace is not in herdr workspace list." -Evidence $script:Caller.workspace_id
    }
    if ($WorkspaceId) {
        if ($liveWs -notcontains $WorkspaceId) {
            Stop-Orch -Code 'WORKSPACE_INVALID' -Message "WorkspaceId '$WorkspaceId' is not a live Herdr workspace." -Evidence ($liveWs -join ', ') -Next "Pass a workspace_id from herdr workspace list."
        }
    }

    if (-not (Test-Path -LiteralPath (Join-Path $script:RepoRoot 'openspec'))) {
        Stop-Orch -Code 'OPENSPEC_ROOT_MISSING' -Message "Repository is missing an openspec directory." -Evidence $script:RepoRoot
    }

    Write-OrchLog -Level 'PREFLIGHT' -Message ("caller pane={0} tab={1} workspace={2} agent={3}" -f $script:Caller.pane_id, $script:Caller.tab_id, $script:Caller.workspace_id, $script:Caller.agent)
    Write-OrchLog -Level 'PREFLIGHT' -Message ("herdr server running version={0}" -f (Get-PropertyValue $server 'version'))
}

function Get-LiveAgents {
    $list = Invoke-HerdrReadOnly agent list
    $agents = @()
    if ($list.Result -and $list.Result.agents) {
        $agents = @($list.Result.agents)
    }
    return $agents
}

function Resolve-LiveAgent {
    param(
        [Parameter(Mandatory = $true)][string]$Target,
        [object[]]$Agents,
        [string]$Role
    )
    $byName = @($Agents | Where-Object { (Get-PropertyValue $_ 'name') -and $_.name -eq $Target })
    if ($byName.Count -eq 1) { return $byName[0] }
    if ($byName.Count -gt 1) {
        Stop-Orch -Code 'AGENT_AMBIGUOUS' -Message "$Role target '$Target' matches multiple live agent names." -Evidence (($byName | ForEach-Object { $_.pane_id }) -join ', ')
    }

    $byPane = @($Agents | Where-Object { $_.pane_id -eq $Target })
    if ($byPane.Count -eq 1) { return $byPane[0] }
    if ($byPane.Count -gt 1) {
        Stop-Orch -Code 'AGENT_AMBIGUOUS' -Message "$Role pane '$Target' matched more than one agent record."
    }

    $byKind = @($Agents | Where-Object { $_.agent -eq $Target })
    if ($byKind.Count -eq 1) {
        Write-OrchLog -Level 'WARN' -Message ("$Role target '$Target' is a kind label; using live pane_id {0} from herdr agent list." -f $byKind[0].pane_id)
        return $byKind[0]
    }
    if ($byKind.Count -gt 1) {
        $detail = ($byKind | ForEach-Object { "{0} ({1})" -f $_.pane_id, $_.workspace_id }) -join ', '
        Stop-Orch -Code 'AGENT_AMBIGUOUS' -Message "$Role target '$Target' is an agent kind with multiple live panes." -Evidence $detail -Next "Pass a unique agent name or pane ID from herdr agent list."
    }

    $wsList = Invoke-HerdrReadOnly workspace list
    $workspaces = @()
    if ($wsList.Result -and $wsList.Result.workspaces) {
        $workspaces = @($wsList.Result.workspaces)
    }
    $byLabel = @($workspaces | Where-Object {
            $label = Get-PropertyValue $_ 'label'
            $label -and ([string]$label).ToLowerInvariant() -eq $Target.ToLowerInvariant()
        })
    if ($byLabel.Count -eq 1) {
        $wsId = [string]$byLabel[0].workspace_id
        $inWs = @($Agents | Where-Object { $_.workspace_id -eq $wsId })
        if ($inWs.Count -eq 1) {
            Write-OrchLog -Level 'WARN' -Message ("$Role target '$Target' matched Herdr workspace label {0}; using live pane_id {1}." -f $wsId, $inWs[0].pane_id)
            return $inWs[0]
        }
        if ($inWs.Count -gt 1) {
            $detail = ($inWs | ForEach-Object { $_.pane_id }) -join ', '
            Stop-Orch -Code 'AGENT_AMBIGUOUS' -Message "$Role workspace label '$Target' has multiple live agents." -Evidence $detail
        }
    }

    Stop-Orch -Code 'AGENT_NOT_FOUND' -Message "$Role target '$Target' is not a live Herdr agent name, pane ID, unique kind, or workspace label." -Evidence "Use herdr agent list and herdr workspace list JSON." -Next "Pass a unique live name (example: commandcode), a pane_id (example: w2:p1), or a unique workspace label (example: Antigravity)."
}

function Get-AgentHandle {
    param($Agent)
    $name = Get-PropertyValue $Agent 'name'
    if ($name) { return [string]$name }
    return [string]$Agent.pane_id
}

function Assert-ProjectWorkspace {
    param($Agent, [string]$Role, $Snapshot)
    $cwd = Get-PropertyValue $Agent 'cwd'
    if (-not $cwd) {
        Stop-Orch -Code 'PROJECT_WORKSPACE_MISMATCH' -Message "$Role pane $($Agent.pane_id) has no cwd in Herdr JSON."
    }
    $ok = $false
    foreach ($root in @($Snapshot.AllowedRoots)) {
        if (Test-PathUnderRoot -Path $cwd -Root $root) { $ok = $true; break }
    }
    if (-not $ok) {
        Stop-Orch -Code 'PROJECT_WORKSPACE_MISMATCH' -Message "$Role cwd is outside the OpenSpec allowed edit roots." -Evidence $cwd -Next ("Allowed roots: {0}" -f ($Snapshot.AllowedRoots -join ', '))
    }
}

function Select-RoleAgent {
    param(
        [string]$Requested,
        [string]$Role,
        [object[]]$Agents,
        [string[]]$ExcludePaneIds,
        $Snapshot
    )

    $pool = @($Agents)
    if ($WorkspaceId) {
        $pool = @($pool | Where-Object { $_.workspace_id -eq $WorkspaceId })
    }
    $pool = @($pool | Where-Object { $ExcludePaneIds -notcontains $_.pane_id })

    $selected = $null
    if ($Requested) {
        $selected = Resolve-LiveAgent -Target $Requested -Agents $Agents -Role $Role
        if ($selected.pane_id -eq $script:Caller.pane_id) {
            Stop-Orch -Code 'AGENT_INVALID' -Message "Refusing to use the orchestrator caller pane as $Role. That would deadlock the wait loop." -Evidence $selected.pane_id
        }
        if ($ExcludePaneIds -contains $selected.pane_id) {
            Stop-Orch -Code 'AGENT_INVALID' -Message "$Role target '$Requested' resolves to a pane that cannot be used for this role." -Evidence $selected.pane_id
        }
        if ($WorkspaceId -and $selected.workspace_id -ne $WorkspaceId) {
            Stop-Orch -Code 'WORKSPACE_MISMATCH' -Message "$Role pane $($selected.pane_id) is in workspace $($selected.workspace_id), not -WorkspaceId $WorkspaceId."
        }
    }
    else {
        $eligible = @($pool | Where-Object { $_.agent })
        if ($eligible.Count -eq 0) {
            Stop-Orch -Code 'AGENT_NOT_FOUND' -Message "No live $Role agent is available." -Next "Start the agent in Herdr, then pass -$Role <name-or-pane-id>."
        }
        if ($eligible.Count -gt 1) {
            $detail = ($eligible | ForEach-Object {
                    $label = Get-AgentHandle $_
                    "{0} kind={1} workspace={2} cwd={3}" -f $label, $_.agent, $_.workspace_id, $_.cwd
                }) -join '; '
            Stop-Orch -Code 'AGENT_AMBIGUOUS' -Message "Multiple live agents could be the $Role. Pass -$Role explicitly." -Evidence $detail
        }
        $selected = $eligible[0]
    }

    $fresh = Invoke-HerdrReadOnly agent get (Get-AgentHandle $selected)
    $live = Get-PropertyValue $fresh.Result 'agent'
    if (-not $live) {
        Stop-Orch -Code 'PANE_INVALID' -Message "herdr agent get did not return agent info for $Role." -Evidence (Get-AgentHandle $selected)
    }
    $pane = Invoke-HerdrReadOnly pane get $live.pane_id
    if (-not (Get-PropertyValue $pane.Result 'pane')) {
        Stop-Orch -Code 'PANE_INVALID' -Message "herdr pane get failed for $Role pane $($live.pane_id)."
    }
    Assert-ProjectWorkspace -Agent $live -Role $Role -Snapshot $Snapshot

    if ($live.pane_id -eq $script:Caller.pane_id) {
        Stop-Orch -Code 'AGENT_INVALID' -Message "Refusing to use the orchestrator caller pane as $Role. That would deadlock the wait loop." -Evidence $live.pane_id
    }

    return $live
}

function ConvertTo-AgentRecord {
    param($Agent, [string]$Role)
    return [pscustomobject]@{
        role           = $Role
        handle         = Get-AgentHandle $Agent
        name           = Get-PropertyValue $Agent 'name'
        kind           = Get-PropertyValue $Agent 'agent'
        pane_id        = [string]$Agent.pane_id
        tab_id         = [string]$Agent.tab_id
        workspace_id   = [string]$Agent.workspace_id
        cwd            = [string](Get-PropertyValue $Agent 'cwd')
        agent_status   = [string](Get-PropertyValue $Agent 'agent_status')
        terminal_id    = [string](Get-PropertyValue $Agent 'terminal_id')
        state_change_seq = Get-PropertyValue $Agent 'state_change_seq'
    }
}

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

function Get-AgentSnapshot {
    param($Record)
    $get = Invoke-HerdrReadOnly agent get $Record.handle
    $agent = Get-PropertyValue $get.Result 'agent'
    if (-not $agent) {
        return [pscustomobject]@{
            Kind     = 'missing'
            Status   = 'missing'
            Agent    = $null
            Handle   = $Record.handle
            Raw      = $get
        }
    }
    if ($agent.pane_id -ne $Record.pane_id) {
        Write-OrchLog -Level 'WARN' -Message ("{0} handle {1} moved from {2} to {3}; adopting live pane_id from Herdr JSON." -f $Record.role, $Record.handle, $Record.pane_id, $agent.pane_id)
        $Record.pane_id = [string]$agent.pane_id
        $Record.tab_id = [string]$agent.tab_id
        $Record.workspace_id = [string]$agent.workspace_id
    }
    $status = [string](Get-PropertyValue $agent 'agent_status')
    return [pscustomobject]@{
        Kind   = $status
        Status = $status
        Agent  = $agent
        Handle = (Get-AgentHandle $agent)
        Raw    = $get
    }
}

function Save-AgentTranscript {
    param(
        [Parameter(Mandatory = $true)]$Record,
        [Parameter(Mandatory = $true)][string]$Label
    )
    if (-not (Test-Path -LiteralPath $script:TranscriptDir)) {
        New-Item -ItemType Directory -Path $script:TranscriptDir -Force | Out-Null
    }
    $read = Invoke-Herdr agent read $Record.handle --source recent-unwrapped --lines 200 -AllowFailure
    $text = ''
    if ($read.Result -and $read.Result.read) {
        $text = [string](Get-PropertyValue $read.Result.read 'text')
    }
    elseif ($read.Text) {
        $text = $read.Text
    }
    $name = "{0}-{1}-{2}.txt" -f ((Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')), $Record.role, $Label
    $path = Join-Path $script:TranscriptDir $name
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($path, $text, $utf8)
    return [pscustomobject]@{
        Path      = $path
        Text      = $text
        Truncated = [bool](Get-PropertyValue (Get-PropertyValue $read.Result 'read') 'truncated')
    }
}

function Parse-StructuredReport {
    param([string]$Text)
    if (-not $Text) {
        return [pscustomobject]@{ Present = $false }
    }

    $status = $null
    if ($Text -match '(?im)^\s*(?:#{1,3}\s*)?Status\s*[:=]\s*([A-Z_]+)') {
        $status = $Matches[1].ToUpperInvariant()
    }
    $validation = $null
    if ($Text -match '(?im)^\s*(?:#{1,3}\s*)?Validation\s*[:=]\s*(.+)$') {
        $validation = $Matches[1].Trim()
    }
    elseif ($Text -match '(?is)##\s*Validation\s*\r?\n(.+?)(?:\r?\n##\s|\z)') {
        $validation = $Matches[1].Trim()
    }
    $verdict = $null
    if ($Text -match '(?im)^\s*(?:#{1,3}\s*)?Verdict\s*[:=]\s*([A-Z_]+)') {
        $verdict = $Matches[1].ToUpperInvariant()
    }

    $findings = New-Object System.Collections.Generic.List[string]
    if ($Text -match '(?is)##\s*Findings\s*\r?\n(.+?)(?:\r?\n##\s|\z)') {
        foreach ($line in ($Matches[1] -split '\r?\n')) {
            $trim = $line.Trim()
            if ($trim -match '^(?:[-*]\s+|\d+\.\s+)') {
                $findings.Add($trim) | Out-Null
            }
        }
    }

    $present = [bool]($status -or $verdict -or $validation -or $Text -match '(?im)^\s*##\s*Summary')
    return [pscustomobject]@{
        Present    = $present
        Status     = $status
        Validation = $validation
        Verdict    = $verdict
        Findings   = @($findings)
        Raw        = $Text
    }
}

function Get-ValidationKind {
    param([string]$Text)
    if (-not $Text) { return 'missing' }
    $t = $Text.ToLowerInvariant()
    if ($t -match '\b(pass|passed|ok|success|succeeded)\b' -and $t -notmatch '\b(fail|failed|error)\b') { return 'pass' }
    if ($t -match '\b(fail|failed|error|not run|missing)\b') { return 'fail' }
    if ($t -match '\bskip|n/a|none required\b') { return 'skipped' }
    return 'unknown'
}

function Resolve-TurnOutcome {
    param(
        [Parameter(Mandatory = $true)]$Record,
        [Parameter(Mandatory = $true)]$SnapshotBefore,
        [Parameter(Mandatory = $true)]$WaitResult,
        [string]$ExpectedRole
    )

    if ($WaitResult.ErrorCode -eq 'agent_prompt_stalled') {
        return [pscustomobject]@{ Kind = 'stalled'; Reason = $WaitResult.ErrorMessage; Report = $null; AgentStatus = 'unknown' }
    }
    if ($WaitResult.ErrorCode -match 'timeout') {
        # Fall through to inspect current state; timeout is only terminal if still working.
    }
    if ($WaitResult.ErrorCode -eq 'agent_not_found') {
        return [pscustomobject]@{ Kind = 'missing'; Reason = $WaitResult.ErrorMessage; Report = $null; AgentStatus = 'missing' }
    }

    $now = Get-AgentSnapshot -Record $Record
    if ($now.Kind -eq 'missing') {
        return [pscustomobject]@{ Kind = 'missing'; Reason = 'Agent disappeared during wait.'; Report = $null; AgentStatus = 'missing' }
    }

    $transcript = Save-AgentTranscript -Record $Record -Label $ExpectedRole
    $report = Parse-StructuredReport -Text $transcript.Text
    $status = $now.Status

    switch ($status) {
        'working' {
            return [pscustomobject]@{ Kind = 'working'; Reason = 'Agent is still working.'; Report = $report; AgentStatus = $status; Transcript = $transcript }
        }
        'blocked' {
            return [pscustomobject]@{ Kind = 'blocked'; Reason = 'Herdr reports a blocked approval or question UI.'; Report = $report; AgentStatus = $status; Transcript = $transcript }
        }
        'unknown' {
            return [pscustomobject]@{ Kind = 'unknown'; Reason = 'Herdr cannot classify the agent confidently.'; Report = $report; AgentStatus = $status; Transcript = $transcript }
        }
        'idle' { }
        'done' { }
        default {
            return [pscustomobject]@{ Kind = 'unknown'; Reason = "Unhandled agent_status '$status'."; Report = $report; AgentStatus = $status; Transcript = $transcript }
        }
    }

    $after = Get-OpenSpecSnapshot
    $beforeRemaining = [int]$SnapshotBefore.Progress.remaining
    $afterRemaining = [int]$after.Progress.remaining
    $checkboxMoved = ($afterRemaining -lt $beforeRemaining)
    $validationKind = Get-ValidationKind $report.Validation
    $explicitFail = ($report.Status -in @('FAILED', 'FAIL', 'ERROR'))
    $explicitBlock = ($report.Status -in @('BLOCKED', 'BLOCK'))
    $explicitComplete = ($report.Status -in @('COMPLETE', 'DONE', 'SUCCESS', 'PASSED', 'OK', 'PARTIAL'))

    if ($explicitFail) {
        return [pscustomobject]@{ Kind = 'failed'; Reason = 'Agent report Status is FAILED.'; Report = $report; AgentStatus = $status; Transcript = $transcript; OpenSpec = $after }
    }
    if ($explicitBlock) {
        return [pscustomobject]@{ Kind = 'blocked'; Reason = 'Agent report Status is BLOCKED.'; Report = $report; AgentStatus = $status; Transcript = $transcript; OpenSpec = $after }
    }

    $completeEnough = $report.Present -and $explicitComplete -and ($validationKind -ne 'missing') -and ($checkboxMoved -or $afterRemaining -eq 0 -or $ExpectedRole -eq 'reviewer' -or $ExpectedRole -eq 'repair' -or $ExpectedRole -eq 'validate')
    if ($ExpectedRole -eq 'reviewer') {
        $completeEnough = $report.Present -and ($report.Verdict -or $report.Status)
    }
    if ($script:SmokeTest) {
        $completeEnough = $report.Present -and $explicitComplete
        if ($ExpectedRole -eq 'reviewer') {
            $completeEnough = $report.Present -and ($report.Verdict -or $report.Status)
        }
    }
    if ($completeEnough) {
        return [pscustomobject]@{
            Kind        = 'complete'
            Reason      = 'Settled state plus structured report and supporting evidence.'
            Report      = $report
            AgentStatus = $status
            Transcript  = $transcript
            OpenSpec    = $after
            CheckboxMoved = $checkboxMoved
            Validation  = $validationKind
        }
    }

    return [pscustomobject]@{
        Kind          = 'settled_incomplete'
        Reason        = 'idle/done is not completion. Missing report, validation, or OpenSpec evidence.'
        Report        = $report
        AgentStatus   = $status
        Transcript    = $transcript
        OpenSpec      = $after
        CheckboxMoved = $checkboxMoved
        Validation    = $validationKind
    }
}

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

function Get-CommonGuardrails {
    param($Snapshot)
    $context = ($Snapshot.ContextFiles | ForEach-Object { "  - $_" }) -join [Environment]::NewLine
    $dirty = @($script:State.git_snapshot)
    $dirtyText = if ($dirty.Count -gt 0) { ($dirty | ForEach-Object { "  $_" }) -join [Environment]::NewLine } else { '  (clean)' }
    $roots = ($Snapshot.AllowedRoots | ForEach-Object { "  - $_" }) -join [Environment]::NewLine
    return @"
Repository: $($script:RepoRoot)
OpenSpec change: $ChangeName
Allowed edit roots:
$roots

Read this OpenSpec context before editing:
$context

Protect the user's existing uncommitted work. Do not revert or overwrite these paths unless the current task explicitly owns them:
$dirtyText

Hard rules:
- Work only through this pane. Do not start other agent CLIs.
- Use apply_patch / your native file-edit tool. Keep diffs focused.
- Edit only inside the allowed roots above.
- Do not edit proposal.md, design.md, or specs/ unless the user has already confirmed that planning change.
- Do not run git commit, git push, git reset, git clean, or recursive deletes.
- Do not mark an OpenSpec checkbox complete unless validation for that task passed.
- Do not invent workspace, tab, or pane IDs.
"@
}

function New-ImplementerPrompt {
    param($Snapshot, $Task)
    $pending = @($Snapshot.Pending | Select-Object -First 12 | ForEach-Object { "  - [$($_.id)] $($_.description)" }) -join [Environment]::NewLine
    $more = $Snapshot.Pending.Count - 12
    if ($more -gt 0) { $pending += [Environment]::NewLine + "  - ... $more more pending tasks" }
    return @"
You are the implementation agent for OpenSpec change '$ChangeName'.

$(Get-CommonGuardrails $Snapshot)

Do the next pending task in dependency / file order. Implement only this task:
- id: $($Task.id)
- $($Task.description)

Remaining tasks after this one (do not start them now):
$pending

Requirements:
- Read the full OpenSpec context listed above before editing.
- Follow task dependencies. Do not skip ahead.
- Run the validation that this task requires before marking it complete in tasks.md.
- If blocked, stop and report instead of guessing.

When finished, reply with exactly these sections:
Status: COMPLETE | PARTIAL | BLOCKED | FAILED
Summary:
Files Read:
Files Changed:
Findings:
Validation:
Risks:
Next Steps:
"@
}

function Get-BoundedReportText {
    param([string]$Text, [int]$MaxChars = 4000)
    if (-not $Text) { return '(no implementer report text captured)' }
    if ($Text.Length -le $MaxChars) { return $Text }
    return "[truncated to last $MaxChars chars]`n" + $Text.Substring($Text.Length - $MaxChars)
}

function New-ReviewerPrompt {
    param($Snapshot, $Task, $ImplementerReport)
    $impl = Get-BoundedReportText $ImplementerReport
    return @"
You are the reviewer agent for OpenSpec change '$ChangeName'. Review only. Do not implement, edit product files, commit, or push.

$(Get-CommonGuardrails $Snapshot)

Task under review:
- id: $($Task.id)
- $($Task.description)

Implementer report:
$impl

Review the current diff and the files named above against the OpenSpec specs and tasks. Hunt for regressions, missing validation, and scope creep.

Reply with exactly these sections:
Status: COMPLETE | BLOCKED | FAILED
Verdict: APPROVE | REPAIR | BLOCK
Summary:
Files Read:
Files Changed:
Findings:
Validation:
Risks:
Next Steps:

Each finding must be a single bullet with severity high, medium, or low and a concrete file or behavior. If there are no findings, write Findings: none.
"@
}

function New-RepairPrompt {
    param($Snapshot, $Task, $Findings)
    $findingText = if ($Findings -and $Findings.Count -gt 0) { ($Findings | ForEach-Object { "  $_" }) -join [Environment]::NewLine } else { '  (see reviewer transcript)' }
    return @"
You are the implementation agent repairing OpenSpec change '$ChangeName'.

$(Get-CommonGuardrails $Snapshot)

Stay on this task:
- id: $($Task.id)
- $($Task.description)

Fix only these reviewer findings:
$findingText

Do not expand scope. Re-run the validation this task requires. Update the tasks.md checkbox only if validation passes.

Reply with exactly these sections:
Status: COMPLETE | PARTIAL | BLOCKED | FAILED
Summary:
Files Read:
Files Changed:
Findings:
Validation:
Risks:
Next Steps:
"@
}

function New-ValidatePrompt {
    param($Snapshot, $Task)
    return @"
Re-run validation for OpenSpec change '$ChangeName', task $($Task.id): $($Task.description)

$(Get-CommonGuardrails $Snapshot)

Do not start new feature work. Run the tests or checks this task requires and report the result. If validation fails, leave the checkbox unchecked.

Reply with exactly these sections:
Status: COMPLETE | PARTIAL | BLOCKED | FAILED
Summary:
Files Read:
Files Changed:
Findings:
Validation:
Risks:
Next Steps:
"@
}

function New-SmokeImplementerPrompt {
    param($Snapshot)
    return @"
You are the implementation agent in a Herdr orchestrator SMOKE TEST for OpenSpec change '$ChangeName'.

$(Get-CommonGuardrails $Snapshot)

This is not a real implementation task. The OpenSpec change is already complete.

Do exactly this:
- Read openspec/changes/$ChangeName/tasks.md and confirm it exists.
- Do not edit any file.
- Do not mark any checkbox.
- Do not run git commit, push, reset, or clean.
- Do not start other agents.

Then reply with exactly these sections:
Status: COMPLETE | PARTIAL | BLOCKED | FAILED
Summary:
Files Read:
Files Changed:
Findings:
Validation:
Risks:
Next Steps:

Use Validation: skipped (smoke test). Files Changed must be none.
"@
}

function New-SmokeReviewerPrompt {
    param($Snapshot, $ImplementerReport)
    $impl = Get-BoundedReportText $ImplementerReport
    return @"
You are the reviewer agent in a Herdr orchestrator SMOKE TEST for OpenSpec change '$ChangeName'. Review only.

$(Get-CommonGuardrails $Snapshot)

This is not a product review. Check only that the implementer:
- produced the required report sections
- did not edit files
- did not commit or push

Implementer report:
$impl

Do not implement, edit files, commit, or push.

Reply with exactly these sections:
Status: COMPLETE | BLOCKED | FAILED
Verdict: APPROVE | REPAIR | BLOCK
Summary:
Files Read:
Files Changed:
Findings:
Validation:
Risks:
Next Steps:

If the implementer stayed read-only, Verdict: APPROVE and Findings: none.
"@
}

function New-StatusNudgePrompt {
    return @"
Your previous turn settled, but the orchestrator could not confirm completion.

Reply now with the required report sections only. Do not change more files unless a previous edit is unfinished and unsafe to leave.

Status: COMPLETE | PARTIAL | BLOCKED | FAILED
Summary:
Files Read:
Files Changed:
Findings:
Validation:
Risks:
Next Steps:
"@
}

# ---------------------------------------------------------------------------
# Dispatch / wait
# ---------------------------------------------------------------------------

function Send-AgentPrompt {
    param(
        [Parameter(Mandatory = $true)]$Record,
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][int]$TimeoutMs
    )
    $script:State.last_dispatch = @{
        at      = (Get-Date).ToUniversalTime().ToString('o')
        role    = $Record.role
        handle  = $Record.handle
        pane_id = $Record.pane_id
        preview = $(if ($Text.Length -gt 240) { $Text.Substring(0, 240) + '...' } else { $Text })
    }
    Save-OrchState
    Write-OrchEvent -Name 'dispatch' -Reason ("prompt {0} {1}" -f $Record.role, $Record.handle)

    return Invoke-HerdrMutation -Target $Record.handle -Action 'herdr agent prompt --wait' -HerdrArgs @(
        'agent', 'prompt', $Record.handle, $Text, '--wait', '--timeout', [string]$TimeoutMs
    )
}

function Wait-AgentSettled {
    param(
        [Parameter(Mandatory = $true)]$Record,
        [Parameter(Mandatory = $true)][int]$TimeoutMs
    )
    return Invoke-HerdrMutation -Target $Record.handle -Action 'herdr agent wait' -HerdrArgs @(
        'agent', 'wait', $Record.handle, '--timeout', [string]$TimeoutMs
    )
}

function Test-HerdrSkipped {
    param($Result)
    if (-not $Result) { return $false }
    $prop = $Result.PSObject.Properties['Skipped']
    return [bool]($prop -and $prop.Value)
}

function Invoke-AgentTurn {
    param(
        [Parameter(Mandatory = $true)]$Record,
        [Parameter(Mandatory = $true)][string]$Prompt,
        [Parameter(Mandatory = $true)]$SnapshotBefore,
        [Parameter(Mandatory = $true)][string]$ExpectedRole,
        [switch]$CollectOnly
    )

    if (-not $script:MutationsAllowed) {
        Write-OrchLog -Level 'DRYRUN' -Message ("planned {0} prompt to {1} ({2})" -f $ExpectedRole, $Record.handle, $Record.pane_id)
        Write-Host $Prompt
        return [pscustomobject]@{ Kind = 'dry_run'; Reason = 'DryRun/WhatIf'; Report = $null }
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $sent = [bool]$CollectOnly
    $stallRetries = 0
    $nudgeSent = $false
    $last = $null
    if ($CollectOnly) {
        Write-OrchLog -Level 'WAIT' -Message ("collect-only for {0}; not sending a new prompt" -f $Record.handle)
    }

    while ((Get-Date) -lt $deadline) {
        $remainingMs = [int][Math]::Max(5000, ($deadline - (Get-Date)).TotalMilliseconds)
        $chunkMs = [Math]::Min($PollSeconds * 1000, $remainingMs)
        $snap = Get-AgentSnapshot -Record $Record

        if ($snap.Kind -eq 'missing') {
            return [pscustomobject]@{ Kind = 'missing'; Reason = 'Agent is not live.'; AgentStatus = 'missing' }
        }

        $waitResult = $null
        if (-not $sent) {
            if ($snap.Status -eq 'working') {
                Write-OrchLog -Level 'WAIT' -Message ("{0} is already working; waiting for settle before a new prompt." -f $Record.handle)
                $waitResult = Wait-AgentSettled -Record $Record -TimeoutMs $chunkMs
            }
            elseif ($snap.Status -eq 'blocked') {
                return [pscustomobject]@{ Kind = 'blocked'; Reason = 'Agent is blocked before dispatch.'; AgentStatus = 'blocked' }
            }
            else {
                $waitResult = Send-AgentPrompt -Record $Record -Text $Prompt -TimeoutMs $chunkMs
                $sent = $true
                if (Test-HerdrSkipped $waitResult) {
                    return [pscustomobject]@{ Kind = 'dry_run'; Reason = 'prompt skipped' }
                }
            }
        }
        else {
            if ($snap.Status -eq 'working') {
                $waitResult = Wait-AgentSettled -Record $Record -TimeoutMs $chunkMs
            }
            else {
                $waitResult = [pscustomobject]@{ Ok = $true; ErrorCode = $null; ErrorMessage = $null }
            }
        }

        if (Test-HerdrSkipped $waitResult) {
            return [pscustomobject]@{ Kind = 'dry_run'; Reason = 'wait skipped' }
        }

        $last = Resolve-TurnOutcome -Record $Record -SnapshotBefore $SnapshotBefore -WaitResult $(if ($waitResult) { $waitResult } else { [pscustomobject]@{ ErrorCode = $null } }) -ExpectedRole $ExpectedRole
        $script:State.last_wait = @{
            at     = (Get-Date).ToUniversalTime().ToString('o')
            role   = $Record.role
            kind   = $last.Kind
            status = $last.AgentStatus
            reason = $last.Reason
        }
        Save-OrchState
        Write-OrchLog -Level 'WAIT' -Message ("{0} lifecycle={1} herdr={2} :: {3}" -f $Record.handle, $last.Kind, $last.AgentStatus, $last.Reason)

        switch ($last.Kind) {
            'complete' { return $last }
            'failed' { return $last }
            'blocked' { return $last }
            'missing' { return $last }
            'working' { continue }
            'stalled' {
                if ($stallRetries -lt 1) {
                    $stallRetries++
                    $sent = $false
                    Write-OrchLog -Level 'WARN' -Message "Prompt stalled; retrying once."
                    continue
                }
                return $last
            }
            'unknown' {
                return $last
            }
            'settled_incomplete' {
                if (-not $nudgeSent) {
                    $nudgeSent = $true
                    $sent = $true
                    Write-OrchLog -Level 'WAIT' -Message "Settled without completion evidence; requesting the structured report once."
                    $null = Send-AgentPrompt -Record $Record -Text (New-StatusNudgePrompt) -TimeoutMs $chunkMs
                    continue
                }
                return $last
            }
            default { return $last }
        }
    }

    if ($last) { return $last }
    return [pscustomobject]@{ Kind = 'timeout'; Reason = "Turn exceeded TimeoutSeconds=$TimeoutSeconds."; AgentStatus = 'unknown' }
}

function Get-FindingList {
    param($Outcome)
    if ($Outcome.Report -and $Outcome.Report.Findings) {
        $items = @($Outcome.Report.Findings | Where-Object {
                $_ -and $_ -notmatch '(?i)\bnone\b' -and $_ -notmatch '(?i)no findings'
            })
        return $items
    }
    return @()
}

function Test-ReviewApproved {
    param($Outcome)
    if (-not $Outcome.Report) { return $false }
    $verdict = $Outcome.Report.Verdict
    $findings = @(Get-FindingList $Outcome)
    $high = @($findings | Where-Object { $_ -match '(?i)\bhigh\b' })
    if ($verdict -eq 'APPROVE' -and $high.Count -eq 0) { return $true }
    if ($verdict -eq 'BLOCK') { return $false }
    if ($verdict -eq 'REPAIR') { return $false }
    if ($findings.Count -eq 0 -and $Outcome.Kind -eq 'complete') { return $true }
    return $false
}

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

function Write-FinalReport {
    param(
        [Parameter(Mandatory = $true)][string]$Result,
        [string]$Reason
    )
    if (-not (Test-Path -LiteralPath $script:ReportDir)) {
        New-Item -ItemType Directory -Path $script:ReportDir -Force | Out-Null
    }
    $snapshot = Get-OpenSpecSnapshot
    $path = Join-Path $script:ReportDir 'final-report.md'
    $impl = $script:State.implementer
    $rev = $script:State.reviewer
    $pending = @($snapshot.Pending | ForEach-Object { "- [$($_.id)] $($_.description)" })
    if ($pending.Count -eq 0) { $pending = @('- none') }
    $body = @"
# Herdr orchestrator report

- Result: $Result
- Change: $ChangeName
- Run: $($script:State.run_id)
- Phase: $($script:State.phase)
- Reason: $Reason
- OpenSpec: $($snapshot.Progress.complete)/$($snapshot.Progress.total) complete (state=$($snapshot.ApplyState))
- Implementer: $(if ($impl) { "{0} pane={1} workspace={2} kind={3}" -f $impl.handle, $impl.pane_id, $impl.workspace_id, $impl.kind } else { 'unset' })
- Reviewer: $(if ($rev) { "{0} pane={1} workspace={2} kind={3}" -f $rev.handle, $rev.pane_id, $rev.workspace_id, $rev.kind } else { 'unset' })
- Review cycle: $($script:State.review_cycle)
- DryRun: $DryRun

## Remaining tasks
$($pending -join [Environment]::NewLine)

## Last wait
$($script:State.last_wait | ConvertTo-Json -Depth 6)

## Blocker
$($script:State.blocker | ConvertTo-Json -Depth 6)

## Note
The orchestrator did not commit, push, reset, or close any workspace/tab/pane it did not create.
"@
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($path, $body, $utf8)
    Write-OrchLog -Level 'REPORT' -Message $path
    Write-Host $body
    return $path
}

function Invoke-SmokeCycle {
    param($Snapshot)

    $task = [pscustomobject]@{
        id          = 'smoke-1'
        description = 'Read-only orchestrator smoke test. Do not edit files or OpenSpec checkboxes.'
        done        = $false
    }
    $script:State.current_task = $task
    Save-OrchState

    if (-not $script:MutationsAllowed) {
        Set-OrchPhase -Phase 'DispatchImplement' -Reason 'DryRun smoke cycle'
        Write-Host '----- smoke implementer prompt -----'
        Write-Host (New-SmokeImplementerPrompt -Snapshot $Snapshot)
        Write-Host '----- smoke reviewer prompt -----'
        Write-Host (New-SmokeReviewerPrompt -Snapshot $Snapshot -ImplementerReport $null)
        $path = Write-FinalReport -Result 'DRYRUN' -Reason 'Planned read-only smoke cycle without dispatching.'
        Set-OrchPhase -Phase 'Complete' -Reason $path
        return 0
    }

    $resumePhase = $script:ResumePhase
    $collectImplement = $Resume -and $resumePhase -eq 'WaitImplement'
    $skipImplement = $Resume -and $resumePhase -in @('Review', 'CollectFindings', 'FinalReport', 'Blocked')

    $implOutcome = $null
    if (-not $skipImplement) {
        if (-not $collectImplement) {
            Set-OrchPhase -Phase 'DispatchImplement' -Reason 'smoke implementer'
        }
        $implPrompt = New-SmokeImplementerPrompt -Snapshot $Snapshot
        Set-OrchPhase -Phase 'WaitImplement' -Reason ("smoke poll {0}s, timeout {1}s" -f $PollSeconds, $TimeoutSeconds)
        $implOutcome = Invoke-AgentTurn -Record $script:State.implementer -Prompt $implPrompt -SnapshotBefore $Snapshot -ExpectedRole 'implementer' -CollectOnly:$collectImplement
    }
    switch ($implOutcome.Kind) {
        'blocked' { Stop-Orch -Code 'AGENT_BLOCKED' -Message "Smoke implementer is blocked." -Evidence $implOutcome.Reason -Next "Resolve the approval in the Antigravity pane, then re-run with -Resume -SmokeTest." }
        'stalled' { Stop-Orch -Code 'AGENT_STALLED' -Message "Smoke implementer prompt stalled twice." -Evidence $implOutcome.Reason }
        'unknown' { Stop-Orch -Code 'AGENT_UNKNOWN' -Message "Smoke implementer state is unknown." -Evidence $implOutcome.Reason }
        'missing' { Stop-Orch -Code 'AGENT_MISSING' -Message "Smoke implementer disappeared." -Evidence $implOutcome.Reason }
        'failed'  { Stop-Orch -Code 'IMPLEMENTATION_FAILED' -Message "Smoke implementer reported FAILED." -Evidence $implOutcome.Reason }
        'timeout' { Stop-Orch -Code 'AGENT_TIMEOUT' -Message "Smoke implementer exceeded TimeoutSeconds." -Evidence $implOutcome.Reason -Next "Re-run with -Resume -SmokeTest." }
        'settled_incomplete' { Stop-Orch -Code 'SETTLED_INCOMPLETE' -Message "Smoke implementer settled without a structured report." -Evidence $implOutcome.Reason }
        'working' { Stop-Orch -Code 'AGENT_TIMEOUT' -Message "Smoke implementer still working after TimeoutSeconds." }
    }

    Set-OrchPhase -Phase 'Review' -Reason 'smoke reviewer'
    $implText = $null
    if ($implOutcome.Transcript) { $implText = $implOutcome.Transcript.Text }
    $reviewPrompt = New-SmokeReviewerPrompt -Snapshot (Get-OpenSpecSnapshot) -ImplementerReport $implText
    $reviewOutcome = Invoke-AgentTurn -Record $script:State.reviewer -Prompt $reviewPrompt -SnapshotBefore (Get-OpenSpecSnapshot) -ExpectedRole 'reviewer'
    switch ($reviewOutcome.Kind) {
        'blocked' { Stop-Orch -Code 'AGENT_BLOCKED' -Message "Smoke reviewer is blocked." -Evidence $reviewOutcome.Reason -Next "Resolve the commandcode pane, then re-run with -Resume -SmokeTest." }
        'stalled' { Stop-Orch -Code 'AGENT_STALLED' -Message "Smoke reviewer prompt stalled twice." -Evidence $reviewOutcome.Reason }
        'unknown' { Stop-Orch -Code 'AGENT_UNKNOWN' -Message "Smoke reviewer state is unknown." -Evidence $reviewOutcome.Reason }
        'missing' { Stop-Orch -Code 'AGENT_MISSING' -Message "Smoke reviewer disappeared." -Evidence $reviewOutcome.Reason }
        'timeout' { Stop-Orch -Code 'AGENT_TIMEOUT' -Message "Smoke reviewer exceeded TimeoutSeconds." -Evidence $reviewOutcome.Reason }
        'failed'  { Stop-Orch -Code 'REVIEW_FAILED' -Message "Smoke reviewer reported FAILED." -Evidence $reviewOutcome.Reason }
        'settled_incomplete' { Stop-Orch -Code 'SETTLED_INCOMPLETE' -Message "Smoke reviewer settled without a structured report." -Evidence $reviewOutcome.Reason }
        'working' { Stop-Orch -Code 'AGENT_TIMEOUT' -Message "Smoke reviewer still working after TimeoutSeconds." }
    }

    Set-OrchPhase -Phase 'CollectFindings' -Reason 'parse smoke review'
    $findings = @(Get-FindingList $reviewOutcome)
    $script:State.last_findings = $findings
    $approved = Test-ReviewApproved $reviewOutcome
    Save-OrchState

    Set-OrchPhase -Phase 'FinalReport' -Reason 'smoke cycle finished'
    $result = 'SMOKE_PASSED'
    $reason = 'Read-only implementer and reviewer cycle finished.'
    if (-not $approved) {
        $result = 'SMOKE_REVIEWED'
        $reason = "Smoke review finished without APPROVE. Findings: $($findings -join ' | ')"
    }
    $path = Write-FinalReport -Result $result -Reason $reason
    Set-OrchPhase -Phase 'Complete' -Reason $path
    return 0
}

# ---------------------------------------------------------------------------
# Main state machine
# ---------------------------------------------------------------------------

function Start-OrchRun {
    Assert-Preflight
    $snapshot = Get-OpenSpecSnapshot
    Write-OrchLog -Level 'PREFLIGHT' -Message ("OpenSpec {0}: {1}/{2} tasks complete (state={3})" -f $ChangeName, $snapshot.Progress.complete, $snapshot.Progress.total, $snapshot.ApplyState)

    $script:ResumePhase = ''
    if ($Resume) {
        $script:State = Import-OrchState
        $script:ResumePhase = [string]$script:State.phase
        Write-OrchLog -Level 'RESUME' -Message ("loaded run {0} phase={1}" -f $script:State.run_id, $script:State.phase)
    }
    else {
        if (Test-Path -LiteralPath $script:StatePath) {
            $existing = Get-Content -LiteralPath $script:StatePath -Raw | ConvertFrom-Json
            $phase = [string](Get-PropertyValue $existing 'phase')
            if ($phase -and $phase -notin @('Complete', 'Failed', 'Blocked')) {
                Stop-Orch -Code 'RESUME_REQUIRED' -Message "An in-progress orchestrator run already exists for '$ChangeName'." -Evidence $script:StatePath -Next "Re-run with -Resume, or move the state file if you intend to start over."
            }
            $backup = Join-Path $script:StateRoot ("state.{0}.{1}.json" -f $phase, (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ'))
            Copy-Item -LiteralPath $script:StatePath -Destination $backup -Force
        }
        $script:State = New-OrchState -Snapshot $snapshot
    }

    $script:State.caller = $script:Caller
    $script:State.git_snapshot = @(Get-GitSnapshot)
    Save-OrchState
    Write-OrchEvent -Name $(if ($Resume) { 'resume' } else { 'start' }) -To $script:State.phase -Reason 'preflight passed'

    Set-OrchPhase -Phase 'Discover' -Reason 'list live Herdr agents and panes'
    $agents = @(Get-LiveAgents)
    if ($agents.Count -eq 0) {
        Stop-Orch -Code 'AGENT_NOT_FOUND' -Message "herdr agent list returned no live agents."
    }
    foreach ($agent in $agents) {
        Write-OrchLog -Level 'DISCOVER' -Message ("{0} kind={1} name={2} workspace={3} status={4} cwd={5}" -f $agent.pane_id, $agent.agent, (Get-PropertyValue $agent 'name'), $agent.workspace_id, $agent.agent_status, (Get-PropertyValue $agent 'cwd'))
    }

    Set-OrchPhase -Phase 'SelectAgents' -Reason 'resolve implementer and reviewer from live JSON'
    $exclude = @($script:Caller.pane_id)
    $implAgent = $null
    if ($Resume -and $script:State.implementer) {
        $implAgent = Select-RoleAgent -Requested $(if ($Implementer) { $Implementer } else { $script:State.implementer.handle }) -Role 'Implementer' -Agents $agents -ExcludePaneIds $exclude -Snapshot $snapshot
    }
    else {
        $implAgent = Select-RoleAgent -Requested $Implementer -Role 'Implementer' -Agents $agents -ExcludePaneIds $exclude -Snapshot $snapshot
    }
    $implRecord = ConvertTo-AgentRecord -Agent $implAgent -Role 'implementer'
    $exclude += $implRecord.pane_id

    $revAgent = $null
    if ($Resume -and $script:State.reviewer) {
        $revAgent = Select-RoleAgent -Requested $(if ($Reviewer) { $Reviewer } else { $script:State.reviewer.handle }) -Role 'Reviewer' -Agents $agents -ExcludePaneIds $exclude -Snapshot $snapshot
    }
    else {
        $revAgent = Select-RoleAgent -Requested $Reviewer -Role 'Reviewer' -Agents $agents -ExcludePaneIds $exclude -Snapshot $snapshot
    }
    $revRecord = ConvertTo-AgentRecord -Agent $revAgent -Role 'reviewer'

    if ((Get-NormalizedPath $implRecord.cwd) -ne (Get-NormalizedPath $revRecord.cwd)) {
        Write-OrchLog -Level 'WARN' -Message "Implementer and reviewer cwd differ, but both are inside the project edit roots."
    }
    if ($implRecord.workspace_id -ne $revRecord.workspace_id) {
        Write-OrchLog -Level 'WARN' -Message ("Implementer workspace {0} and reviewer workspace {1} differ. Both are accepted because they share the project cwd." -f $implRecord.workspace_id, $revRecord.workspace_id)
    }

    $script:State.implementer = $implRecord
    $script:State.reviewer = $revRecord
    Save-OrchState
    Write-OrchLog -Level 'SELECT' -Message ("implementer handle={0} pane={1} workspace={2} kind={3}" -f $implRecord.handle, $implRecord.pane_id, $implRecord.workspace_id, $implRecord.kind)
    Write-OrchLog -Level 'SELECT' -Message ("reviewer handle={0} pane={1} workspace={2} kind={3}" -f $revRecord.handle, $revRecord.pane_id, $revRecord.workspace_id, $revRecord.kind)

    if ($script:SmokeTest) {
        return Invoke-SmokeCycle -Snapshot $snapshot
    }

    if ($snapshot.ApplyState -eq 'all_done' -or [int]$snapshot.Progress.remaining -eq 0) {
        Set-OrchPhase -Phase 'FinalReport' -Reason 'OpenSpec reports no remaining tasks'
        $path = Write-FinalReport -Result 'COMPLETE' -Reason 'All OpenSpec tasks are already complete.'
        Set-OrchPhase -Phase 'Complete' -Reason $path
        return 0
    }

    if (-not $script:MutationsAllowed) {
        $task = $snapshot.Pending[0]
        $script:State.current_task = $task
        Set-OrchPhase -Phase 'DispatchImplement' -Reason 'DryRun/WhatIf planned first task'
        Write-Host "----- implementer prompt -----"
        Write-Host (New-ImplementerPrompt -Snapshot $snapshot -Task $task)
        Write-Host "----- reviewer prompt -----"
        Write-Host (New-ReviewerPrompt -Snapshot $snapshot -Task $task -ImplementerReport $null)
        $path = Write-FinalReport -Result 'DRYRUN' -Reason "Planned first pending task $($task.id) without dispatching."
        Set-OrchPhase -Phase 'Complete' -Reason $path
        return 0
    }

    $resumePhase = [string]$script:State.phase
    $skipToReview = $Resume -and $resumePhase -in @('Review', 'CollectFindings', 'DispatchRepair', 'Validate', 'CheckOpenSpec')

    while ($true) {
        $snapshot = Get-OpenSpecSnapshot
        $script:State.openspec = @{
            apply_state = $snapshot.ApplyState
            complete    = $snapshot.Progress.complete
            total       = $snapshot.Progress.total
            remaining   = $snapshot.Progress.remaining
        }
        Save-OrchState

        if ($snapshot.ApplyState -eq 'all_done' -or [int]$snapshot.Progress.remaining -eq 0) {
            Set-OrchPhase -Phase 'FinalReport' -Reason 'all OpenSpec tasks complete'
            $path = Write-FinalReport -Result 'COMPLETE' -Reason 'All tasks completed through the Herdr loop.'
            Set-OrchPhase -Phase 'Complete' -Reason $path
            return 0
        }

        $task = $null
        if ($script:State.current_task -and $skipToReview) {
            $task = $script:State.current_task
        }
        else {
            $task = $snapshot.Pending[0]
            $script:State.current_task = $task
            $script:State.review_cycle = 0
            $script:State.last_findings = @()
        }
        Save-OrchState
        Write-OrchLog -Level 'TASK' -Message ("{0}/{1} next={2} {3}" -f $snapshot.Progress.complete, $snapshot.Progress.total, $task.id, $task.description)

        $implOutcome = $null
        if (-not $skipToReview) {
            Set-OrchPhase -Phase 'DispatchImplement' -Reason ("task {0}" -f $task.id)
            $implPrompt = New-ImplementerPrompt -Snapshot $snapshot -Task $task
            Set-OrchPhase -Phase 'WaitImplement' -Reason ("poll {0}s, timeout {1}s" -f $PollSeconds, $TimeoutSeconds)
            $implOutcome = Invoke-AgentTurn -Record $script:State.implementer -Prompt $implPrompt -SnapshotBefore $snapshot -ExpectedRole 'implementer'
            switch ($implOutcome.Kind) {
                'blocked' { Stop-Orch -Code 'AGENT_BLOCKED' -Message "Implementer is blocked." -Evidence $implOutcome.Reason -Next "Resolve the approval/question in the implementer pane, then re-run with -Resume." }
                'stalled' { Stop-Orch -Code 'AGENT_STALLED' -Message "Implementer prompt stalled twice." -Evidence $implOutcome.Reason }
                'unknown' { Stop-Orch -Code 'AGENT_UNKNOWN' -Message "Implementer state is unknown." -Evidence $implOutcome.Reason -Next "Inspect the pane, then re-run with -Resume." }
                'missing' { Stop-Orch -Code 'AGENT_MISSING' -Message "Implementer disappeared." -Evidence $implOutcome.Reason }
                'failed'  { Stop-Orch -Code 'IMPLEMENTATION_FAILED' -Message "Implementer reported FAILED." -Evidence $implOutcome.Reason }
                'timeout' { Stop-Orch -Code 'AGENT_TIMEOUT' -Message "Implementer exceeded TimeoutSeconds." -Evidence $implOutcome.Reason -Next "Re-run with -Resume or a larger -TimeoutSeconds." }
                'settled_incomplete' { Stop-Orch -Code 'SETTLED_INCOMPLETE' -Message "Implementer became idle/done without report, validation, and OpenSpec evidence." -Evidence $implOutcome.Reason -Next "Inspect the transcript and re-run with -Resume." }
                'working' { Stop-Orch -Code 'AGENT_TIMEOUT' -Message "Implementer still working after TimeoutSeconds." }
            }
        }

        Set-OrchPhase -Phase 'Review' -Reason ("reviewer {0}" -f $script:State.reviewer.handle)
        $implText = $null
        if ($implOutcome -and $implOutcome.Transcript) { $implText = $implOutcome.Transcript.Text }
        $reviewPrompt = New-ReviewerPrompt -Snapshot (Get-OpenSpecSnapshot) -Task $task -ImplementerReport $implText
        $reviewOutcome = Invoke-AgentTurn -Record $script:State.reviewer -Prompt $reviewPrompt -SnapshotBefore (Get-OpenSpecSnapshot) -ExpectedRole 'reviewer'
        switch ($reviewOutcome.Kind) {
            'blocked' { Stop-Orch -Code 'AGENT_BLOCKED' -Message "Reviewer is blocked." -Evidence $reviewOutcome.Reason -Next "Resolve the reviewer pane, then re-run with -Resume." }
            'stalled' { Stop-Orch -Code 'AGENT_STALLED' -Message "Reviewer prompt stalled twice." -Evidence $reviewOutcome.Reason }
            'unknown' { Stop-Orch -Code 'AGENT_UNKNOWN' -Message "Reviewer state is unknown." -Evidence $reviewOutcome.Reason }
            'missing' { Stop-Orch -Code 'AGENT_MISSING' -Message "Reviewer disappeared." -Evidence $reviewOutcome.Reason }
            'timeout' { Stop-Orch -Code 'AGENT_TIMEOUT' -Message "Reviewer exceeded TimeoutSeconds." -Evidence $reviewOutcome.Reason }
            'failed'  { Stop-Orch -Code 'REVIEW_FAILED' -Message "Reviewer reported FAILED." -Evidence $reviewOutcome.Reason }
        }

        Set-OrchPhase -Phase 'CollectFindings' -Reason 'parse reviewer verdict and findings'
        $findings = @(Get-FindingList $reviewOutcome)
        $script:State.last_findings = $findings
        Save-OrchState
        $approved = Test-ReviewApproved $reviewOutcome

        while (-not $approved) {
            if ($reviewOutcome.Report -and $reviewOutcome.Report.Verdict -eq 'BLOCK') {
                Stop-Orch -Code 'REVIEW_BLOCKED' -Message "Reviewer verdict is BLOCK." -Evidence (($findings -join ' | '))
            }
            if ([int]$script:State.review_cycle -ge $MaxReviewCycles) {
                Stop-Orch -Code 'REVIEW_CYCLES_EXCEEDED' -Message "Reached -MaxReviewCycles $MaxReviewCycles with remaining findings." -Evidence (($findings -join ' | '))
            }

            $script:State.review_cycle = [int]$script:State.review_cycle + 1
            Save-OrchState
            Set-OrchPhase -Phase 'DispatchRepair' -Reason ("repair cycle {0}" -f $script:State.review_cycle)
            $repairPrompt = New-RepairPrompt -Snapshot (Get-OpenSpecSnapshot) -Task $task -Findings $findings
            $repairOutcome = Invoke-AgentTurn -Record $script:State.implementer -Prompt $repairPrompt -SnapshotBefore (Get-OpenSpecSnapshot) -ExpectedRole 'repair'
            switch ($repairOutcome.Kind) {
                'blocked' { Stop-Orch -Code 'AGENT_BLOCKED' -Message "Implementer blocked during repair." -Evidence $repairOutcome.Reason -Next "Resolve the pane, then re-run with -Resume." }
                'stalled' { Stop-Orch -Code 'AGENT_STALLED' -Message "Repair prompt stalled twice." -Evidence $repairOutcome.Reason }
                'unknown' { Stop-Orch -Code 'AGENT_UNKNOWN' -Message "Implementer state is unknown during repair." -Evidence $repairOutcome.Reason }
                'missing' { Stop-Orch -Code 'AGENT_MISSING' -Message "Implementer disappeared during repair." }
                'failed'  { Stop-Orch -Code 'REPAIR_FAILED' -Message "Repair reported FAILED." -Evidence $repairOutcome.Reason }
                'timeout' { Stop-Orch -Code 'AGENT_TIMEOUT' -Message "Repair exceeded TimeoutSeconds." }
                'settled_incomplete' { Stop-Orch -Code 'SETTLED_INCOMPLETE' -Message "Repair settled without completion evidence." -Evidence $repairOutcome.Reason }
            }

            Set-OrchPhase -Phase 'Validate' -Reason 're-run task validation after repair'
            $validatePrompt = New-ValidatePrompt -Snapshot (Get-OpenSpecSnapshot) -Task $task
            $validateOutcome = Invoke-AgentTurn -Record $script:State.implementer -Prompt $validatePrompt -SnapshotBefore (Get-OpenSpecSnapshot) -ExpectedRole 'validate'
            $script:State.last_validation = @{
                at     = (Get-Date).ToUniversalTime().ToString('o')
                kind   = $validateOutcome.Kind
                status = $(if ($validateOutcome.Report) { $validateOutcome.Report.Status } else { $null })
                text   = $(if ($validateOutcome.Report) { $validateOutcome.Report.Validation } else { $null })
            }
            Save-OrchState
            if ($validateOutcome.Kind -in @('blocked', 'failed', 'stalled', 'unknown', 'missing', 'timeout', 'settled_incomplete')) {
                Stop-Orch -Code 'VALIDATION_INCOMPLETE' -Message "Validation turn did not complete cleanly." -Evidence $validateOutcome.Reason
            }

            Set-OrchPhase -Phase 'Review' -Reason ("re-review after repair cycle {0}" -f $script:State.review_cycle)
            $repairText = $null
            if ($repairOutcome.Transcript) { $repairText = $repairOutcome.Transcript.Text }
            $reviewPrompt = New-ReviewerPrompt -Snapshot (Get-OpenSpecSnapshot) -Task $task -ImplementerReport $repairText
            $reviewOutcome = Invoke-AgentTurn -Record $script:State.reviewer -Prompt $reviewPrompt -SnapshotBefore (Get-OpenSpecSnapshot) -ExpectedRole 'reviewer'
            switch ($reviewOutcome.Kind) {
                'blocked' { Stop-Orch -Code 'AGENT_BLOCKED' -Message "Reviewer blocked after repair." -Evidence $reviewOutcome.Reason }
                'stalled' { Stop-Orch -Code 'AGENT_STALLED' -Message "Re-review stalled." }
                'unknown' { Stop-Orch -Code 'AGENT_UNKNOWN' -Message "Reviewer unknown after repair." }
                'missing' { Stop-Orch -Code 'AGENT_MISSING' -Message "Reviewer disappeared after repair." }
                'timeout' { Stop-Orch -Code 'AGENT_TIMEOUT' -Message "Re-review exceeded TimeoutSeconds." }
                'failed'  { Stop-Orch -Code 'REVIEW_FAILED' -Message "Re-review reported FAILED." }
            }
            Set-OrchPhase -Phase 'CollectFindings' -Reason 'parse post-repair review'
            $findings = @(Get-FindingList $reviewOutcome)
            $script:State.last_findings = $findings
            Save-OrchState
            $approved = Test-ReviewApproved $reviewOutcome
        }

        Set-OrchPhase -Phase 'CheckOpenSpec' -Reason 'confirm checkbox and remaining work'
        $after = Get-OpenSpecSnapshot
        $stillPending = @($after.Pending | Where-Object { $_.id -eq $task.id -or $_.description -eq $task.description })
        if ($stillPending.Count -gt 0) {
            Stop-Orch -Code 'OPENSPEC_TASK_UNCHECKED' -Message "Review passed but OpenSpec still lists this task as pending." -Evidence $task.id -Next "Inspect tasks.md and the implementer transcript, then re-run with -Resume."
        }
        $doneIds = @()
        if ($script:State.completed_task_ids) { $doneIds = @($script:State.completed_task_ids) }
        $script:State.completed_task_ids = $doneIds + @($task.id)
        $script:State.current_task = $null
        $skipToReview = $false
        Save-OrchState
        Write-OrchLog -Level 'TASK' -Message ("accepted {0}; OpenSpec {1}/{2}" -f $task.id, $after.Progress.complete, $after.Progress.total)
    }
}

$exitCode = 1
try {
    $exitCode = Start-OrchRun
}
catch {
    $exitCode = 1
    $blockerCode = $null
    if ($_.Exception.Data) { $blockerCode = $_.Exception.Data['blocker_code'] }
    if (-not $blockerCode) {
        Write-OrchLog -Level 'ERROR' -Message $_.Exception.Message
        if ($_.InvocationInfo) {
            Write-OrchLog -Level 'ERROR' -Message ("at {0}:{1}" -f $_.InvocationInfo.ScriptName, $_.InvocationInfo.ScriptLineNumber)
        }
    }
}
exit $exitCode
