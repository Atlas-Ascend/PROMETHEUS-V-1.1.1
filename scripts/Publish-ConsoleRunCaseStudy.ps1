[CmdletBinding()]
param(
    [string]$SummaryPath,
    [string]$Target = "serverforge/case-study-target.json",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8

$Root = Split-Path -Parent $PSScriptRoot
$ApiRoot = "https://discord.com/api/v10"
$EvidenceRoot = Join-Path $Root "artifacts/serverforge-console-runs"

function Resolve-RepoPath {
    param([Parameter(Mandatory)][string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) { return [System.IO.Path]::GetFullPath($Path) }
    return [System.IO.Path]::GetFullPath((Join-Path $Root $Path))
}

function Get-DiscordRetrySeconds {
    param($ErrorRecord, [int]$Attempt)
    try {
        $Payload = $ErrorRecord.ErrorDetails.Message | ConvertFrom-Json
        if ($Payload.retry_after) { return [Math]::Max(1, [Math]::Ceiling([double]$Payload.retry_after)) }
    }
    catch {}
    return [Math]::Min(30, [Math]::Pow(2, $Attempt))
}

function Invoke-DiscordApi {
    param(
        [Parameter(Mandatory)][ValidateSet("GET", "POST")][string]$Method,
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][hashtable]$Headers,
        $Body = $null
    )

    for ($Attempt = 1; $Attempt -le 6; $Attempt++) {
        try {
            $Args = @{
                Method = $Method
                Uri = "$ApiRoot$Path"
                Headers = $Headers
                ErrorAction = "Stop"
            }
            if ($null -ne $Body) {
                $Args.ContentType = "application/json; charset=utf-8"
                $Args.Body = ($Body | ConvertTo-Json -Depth 20 -Compress)
            }
            return Invoke-RestMethod @Args
        }
        catch {
            $Status = $null
            try { $Status = [int]$_.Exception.Response.StatusCode.value__ } catch {}
            if ($Status -eq 429 -and $Attempt -lt 6) {
                Start-Sleep -Seconds (Get-DiscordRetrySeconds -ErrorRecord $_ -Attempt $Attempt)
                continue
            }
            throw "Discord API $Method $Path failed (status=$Status): $($_.Exception.Message)"
        }
    }
    throw "Discord API $Method $Path exhausted retries."
}

function Get-ChannelMap {
    param([Parameter(Mandatory)]$Channels)
    $Map = @{}
    foreach ($Channel in $Channels) {
        if ($Channel.type -eq 0) { $Map[[string]$Channel.name] = [string]$Channel.id }
    }
    return $Map
}

function Publish-IdempotentMessage {
    param(
        [Parameter(Mandatory)][string]$ChannelName,
        [Parameter(Mandatory)][string]$ChannelId,
        [Parameter(Mandatory)][string]$Content,
        [Parameter(Mandatory)][string]$Marker,
        [Parameter(Mandatory)][hashtable]$Headers
    )

    $Final = "$Content`n`n$Marker"
    if ($Final.Length -gt 2000) {
        throw "Discord message for #$ChannelName exceeds 2000 characters ($($Final.Length))."
    }
    if ($DryRun) {
        Write-Host "DRY RUN #$ChannelName · $($Final.Length) chars" -ForegroundColor Yellow
        return [pscustomobject]@{ channel = $ChannelName; status = "dry-run"; message_id = $null; verified = $false }
    }

    $Existing = @(Invoke-DiscordApi -Method GET -Path "/channels/$ChannelId/messages?limit=100" -Headers $Headers) |
        Where-Object { $_.content -and $_.content.Contains($Marker) } |
        Select-Object -First 1
    if ($Existing) {
        return [pscustomobject]@{ channel = $ChannelName; status = "existing"; message_id = [string]$Existing.id; verified = $true }
    }

    $Posted = Invoke-DiscordApi -Method POST -Path "/channels/$ChannelId/messages" -Headers $Headers -Body @{
        content = $Final
        allowed_mentions = @{ parse = @() }
    }
    $Verified = Invoke-DiscordApi -Method GET -Path "/channels/$ChannelId/messages/$($Posted.id)" -Headers $Headers
    if (-not $Verified.content.Contains($Marker)) {
        throw "Discord retrieval verification failed for #$ChannelName message $($Posted.id)."
    }
    return [pscustomobject]@{ channel = $ChannelName; status = "published"; message_id = [string]$Posted.id; verified = $true }
}

$TargetPath = Resolve-RepoPath $Target
if (-not (Test-Path -LiteralPath $TargetPath -PathType Leaf)) { throw "Case-study target not found: $TargetPath" }
$TargetConfig = Get-Content -LiteralPath $TargetPath -Raw -Encoding UTF8 | ConvertFrom-Json

if (-not $SummaryPath) {
    $Latest = Get-ChildItem (Join-Path $Root ".prometheus/runs") -Filter summary.json -File -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1
    if (-not $Latest) { throw "No PROMETHEUS summary.json was found under .prometheus/runs." }
    $SummaryPath = $Latest.FullName
}
$SummaryPath = Resolve-RepoPath $SummaryPath
if (-not (Test-Path -LiteralPath $SummaryPath -PathType Leaf)) { throw "Run summary not found: $SummaryPath" }

$Summary = Get-Content -LiteralPath $SummaryPath -Raw -Encoding UTF8 | ConvertFrom-Json
$ReceiptPath = Resolve-RepoPath ([string]$Summary.receipt)
$GenomePath = Resolve-RepoPath ([string]$Summary.capability_genome)
if (-not (Test-Path -LiteralPath $ReceiptPath -PathType Leaf)) { throw "Promotion receipt not found: $ReceiptPath" }
if (-not (Test-Path -LiteralPath $GenomePath -PathType Leaf)) { throw "Capability genome not found: $GenomePath" }

$Receipt = Get-Content -LiteralPath $ReceiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
$Genome = Get-Content -LiteralPath $GenomePath -Raw -Encoding UTF8 | ConvertFrom-Json

Push-Location $Root
try {
    $env:PYTHONPATH = Join-Path $Root "src"
    python -m prometheus_kernel verify $ReceiptPath | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Promotion receipt verification failed. Discord publication blocked." }
}
finally {
    Pop-Location
}

$GuildId = if ($env:DISCORD_GUILD_ID) { [string]$env:DISCORD_GUILD_ID } else { [string]$TargetConfig.guild_id }
if ($GuildId -ne [string]$TargetConfig.guild_id) { throw "DISCORD_GUILD_ID does not match the authorized case-study target." }

$Candidates = @($Receipt.candidate_results)
$CandidateLines = @()
foreach ($Candidate in $Candidates) {
    $Result = if ($Candidate.standard_test.passed) { "PASS" } else { "FAIL" }
    $CandidateLines += "- ``$($Candidate.candidate_id)`` · $Result · score $($Candidate.score) · $($Candidate.operation_count) operation(s)"
}
$Leader = @($Candidates | Where-Object { $_.candidate_id -eq $Receipt.leader }) | Select-Object -First 1
$ChallengeAttempts = @($Leader.challenge_attempts)
$ChallengeLines = @()
for ($Index = 0; $Index -lt $ChallengeAttempts.Count; $Index++) {
    $Attempt = $ChallengeAttempts[$Index]
    $State = if ($Attempt.passed) { "PASS" } else { "FAIL" }
    $ChallengeLines += "- attempt $($Index + 1): $State · exit $($Attempt.exit_code) · $($Attempt.duration_ms) ms"
}
$Capabilities = @($Genome.capabilities | ForEach-Object { "- ``$_``" })
$ArtifactCount = @($Receipt.artifacts).Count
$EventCount = [int]$Receipt.event_ledger.events
$CreatedAt = [string]$Receipt.created_at
$RunId = [string]$Receipt.run_id
$MarkerBase = "[PROMETHEUS-RUN:$RunId]"

$Messages = [ordered]@{
    "live-case-study" = "🔥 **PROMETHEUS CONSOLE RUN PROMOTED**`nRun: ``$RunId```nMission: ``$($Receipt.mission_id)```nObjective: $($Receipt.objective)`nLeader: ``$($Receipt.leader)```nRepairs applied: ``$($Receipt.repairs_applied)```nReceipt: ``$($Receipt.receipt_hash)```nCreated: ``$CreatedAt``"
    "mission-intake" = "🎯 **MISSION INTAKE**`nRun: ``$RunId```nMission ID: ``$($Receipt.mission_id)```nObjective: $($Receipt.objective)`nCandidates admitted: ``$($Candidates.Count)```nExecution policy: bounded commands, timeouts, output limits, isolated Git worktrees."
    "candidate-forge" = "🏭 **COUNTERFACTUAL CANDIDATE FORGE**`n$($CandidateLines -join "`n")`nSelected leader: ``$($Receipt.leader)``"
    "challenge-queue" = "⚔️ **ADVERSARIAL CHALLENGE QUEUE**`nLeader: ``$($Receipt.leader)```nChallenge attempts: ``$($ChallengeAttempts.Count)```n$($ChallengeLines -join "`n")"
    "findings" = "🔍 **ADVERSARIAL FINDING**`nInitial challenge state: ``$(if ($ChallengeAttempts.Count -gt 0 -and -not $ChallengeAttempts[0].passed) { 'FAILED AS DESIGNED' } else { 'PASSED' })```nRepair path invoked: ``$($Receipt.repairs_applied)```nFinal challenge state: ``$(if ($Leader.challenge.passed) { 'PASS' } else { 'FAIL' })``"
    "repair-verification" = "🛠️ **REPAIR VERIFICATION**`nRepair commits: ``$(@($Leader.repair_commits).Count)```nPost-repair standard gate: ``$(if ($Leader.standard_test.passed) { 'PASS' } else { 'FAIL' })```nPost-repair challenge gate: ``$(if ($Leader.challenge.passed) { 'PASS' } else { 'FAIL' })``"
    "promotion-gate" = "🏛️ **PROMOTION GATE AUTHORIZED**`nPromoted candidate: ``$($Receipt.leader)```nPromoted commit: ``$($Receipt.promoted_commit)```nArtifacts sealed: ``$ArtifactCount```nEvent-chain entries: ``$EventCount```nStatus: ``$($Summary.status)``"
    "promotion-receipts" = "🧾 **PROOFGRID PROMOTION RECEIPT**`nRun: ``$RunId```nReceipt SHA-256: ``$($Receipt.receipt_hash)```nLedger SHA-256: ``$($Receipt.event_ledger.sha256)```nLedger chain head: ``$($Receipt.event_ledger.chain_head)```nIndependent verification: ``python -m prometheus_kernel verify '$ReceiptPath'``"
    "capability-genomes" = "🧬 **CAPABILITY GENOME**`nRun: ``$RunId```nEvidence receipt: ``$($Genome.evidence_receipt_hash)```n$($Capabilities -join "`n")"
    "reproduction-lab" = "🧪 **REPRODUCTION LAB**`n``python -m unittest discover -s tests -v```n``python -m prometheus_kernel run missions/bootstrap.json```n``python -m prometheus_kernel verify '$ReceiptPath'```nExpected result: tests pass, one candidate is promoted, and the receipt verifies."
    "bridge-control" = "⚙️ **SERVERFORGE BRIDGE EVENT**`nGuild: ``$GuildId```nApplication: ``$($TargetConfig.application_id)```nRun: ``$RunId```nMode: authenticated, idempotent, retrieval-verified publication`nSecrets recorded: ``NO``"
    "telemetry" = "📡 **RUNTIME TELEMETRY**`nPython: ``$($Receipt.runtime.python)```nPlatform: ``$($Receipt.runtime.platform)```nCandidates: ``$($Candidates.Count)```nArtifacts: ``$ArtifactCount```nLedger events: ``$EventCount```nRepairs applied: ``$($Receipt.repairs_applied)``"
    "incidents-and-rollback" = "🛡️ **INCIDENT AND RECOVERY STATE**`nRun: ``$RunId```nOpen incident: ``NO```nRepair event retained: ``$($Receipt.repairs_applied)```nRollback anchors: seed commit ``$($Receipt.seed_commit)`` and promoted commit ``$($Receipt.promoted_commit)```nFailure history was preserved rather than erased."
}

if ($DryRun) {
    foreach ($Entry in $Messages.GetEnumerator()) {
        $null = Publish-IdempotentMessage -ChannelName $Entry.Key -ChannelId "dry-run" -Content $Entry.Value -Marker "$MarkerBase:$($Entry.Key)" -Headers @{}
    }
    Write-Host "Console-run case-study dry run passed. No Discord mutation occurred." -ForegroundColor Yellow
    exit 0
}

$Token = $env:DISCORD_BOT_TOKEN
if (-not $Token) { throw "DISCORD_BOT_TOKEN is required for live case-study publication." }
$Headers = @{
    Authorization = "Bot $Token"
    "User-Agent" = "PROMETHEUS-ServerForge/1.1.1 (Console Run Case Study)"
}
$Guild = Invoke-DiscordApi -Method GET -Path "/guilds/$GuildId" -Headers $Headers
if ([string]$Guild.name -ne [string]$TargetConfig.expected_guild_name) {
    throw "Guild name '$($Guild.name)' does not match authorized target '$($TargetConfig.expected_guild_name)'."
}
$ChannelMap = Get-ChannelMap -Channels @(Invoke-DiscordApi -Method GET -Path "/guilds/$GuildId/channels" -Headers $Headers)
$Results = New-Object System.Collections.Generic.List[object]
foreach ($Entry in $Messages.GetEnumerator()) {
    $ChannelId = $ChannelMap[$Entry.Key]
    if (-not $ChannelId) { throw "Required case-study channel was not found: #$($Entry.Key)" }
    $Result = Publish-IdempotentMessage -ChannelName $Entry.Key -ChannelId $ChannelId -Content $Entry.Value -Marker "$MarkerBase:$($Entry.Key)" -Headers $Headers
    $Results.Add($Result)
}

New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null
$ReceiptOut = Join-Path $EvidenceRoot "$RunId-discord-case-study-receipt.json"
$PublicationReceipt = [ordered]@{
    schema = "prometheus.serverforge.console-run-publication.v1"
    run_id = $RunId
    guild_id = $GuildId
    application_id = [string]$TargetConfig.application_id
    source_summary = $SummaryPath
    source_receipt = $ReceiptPath
    source_receipt_hash = [string]$Receipt.receipt_hash
    published_at_utc = [DateTime]::UtcNow.ToString("o")
    all_verified = -not (@($Results | Where-Object { -not $_.verified }).Count)
    secret_material_recorded = $false
    messages = @($Results)
}
[System.IO.File]::WriteAllText($ReceiptOut, (($PublicationReceipt | ConvertTo-Json -Depth 20) + "`n"), $Utf8)

Write-Host "" 
Write-Host "PROMETHEUS console run published to ServerForge." -ForegroundColor Green
Write-Host "Run:     $RunId" -ForegroundColor Cyan
Write-Host "Messages: $($Results.Count)" -ForegroundColor Cyan
Write-Host "Receipt: $ReceiptOut" -ForegroundColor Cyan
$Results | Format-Table channel, status, verified, message_id -AutoSize
