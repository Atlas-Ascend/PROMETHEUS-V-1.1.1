[CmdletBinding()]
param(
    [string]$Publication = "serverforge/publications/GAI-FR-20260721-PROM-SF-001.json",
    [string]$ConfirmGuild = $env:DISCORD_GUILD_ID,
    [switch]$DryRun,
    [switch]$NoPin
)

$ErrorActionPreference = "Stop"
$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8

$Root = Split-Path -Parent $PSScriptRoot
$PublicationPath = Join-Path $Root $Publication
$ReceiptRoot = Join-Path $Root "artifacts/serverforge-publications"
$ApiRoot = "https://discord.com/api/v10"

function Get-Sha256Hex {
    param([Parameter(Mandatory)][string]$Path)
    $Stream = [System.IO.File]::OpenRead($Path)
    try {
        $Hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($Stream)
        return -join ($Hash | ForEach-Object { $_.ToString("x2") })
    }
    finally {
        $Stream.Dispose()
    }
}

function Get-GitHead {
    param([string]$WorkingDirectory)
    try {
        $Head = (& git -C $WorkingDirectory rev-parse HEAD 2>$null).Trim()
        if ($LASTEXITCODE -eq 0 -and $Head) { return $Head }
    }
    catch {}
    return "unknown"
}

function Get-DiscordRetrySeconds {
    param($ErrorRecord, [int]$Attempt)
    try {
        $Text = $ErrorRecord.ErrorDetails.Message
        if ($Text) {
            $Payload = $Text | ConvertFrom-Json
            if ($Payload.retry_after) {
                return [Math]::Max(1, [Math]::Ceiling([double]$Payload.retry_after))
            }
        }
    }
    catch {}
    return [Math]::Min(30, [Math]::Pow(2, $Attempt))
}

function Invoke-DiscordApi {
    param(
        [Parameter(Mandatory)][ValidateSet("GET","POST","PUT")][string]$Method,
        [Parameter(Mandatory)][string]$Path,
        [hashtable]$Headers,
        $Body = $null
    )

    $Uri = "$ApiRoot$Path"
    for ($Attempt = 1; $Attempt -le 6; $Attempt++) {
        try {
            $Args = @{
                Method = $Method
                Uri = $Uri
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
            if (-not $Status) {
                try { $Status = [int]$_.Exception.Response.StatusCode } catch {}
            }
            if ($Status -eq 429 -and $Attempt -lt 6) {
                $Delay = Get-DiscordRetrySeconds -ErrorRecord $_ -Attempt $Attempt
                Write-Host "Discord rate limit encountered; retrying in $Delay second(s)." -ForegroundColor Yellow
                Start-Sleep -Seconds $Delay
                continue
            }
            throw "Discord API $Method $Path failed (status=$Status): $($_.Exception.Message)"
        }
    }
    throw "Discord API $Method $Path exhausted retries."
}

function Get-ChannelByName {
    param(
        [Parameter(Mandatory)]$Channels,
        [Parameter(Mandatory)][string]$Name
    )
    $Matches = @($Channels | Where-Object { $_.type -eq 0 -and $_.name -eq $Name })
    if ($Matches.Count -ne 1) {
        throw "Expected exactly one text channel named '$Name'; found $($Matches.Count)."
    }
    return $Matches[0]
}

function Get-ExistingPublicationMessage {
    param(
        [Parameter(Mandatory)][string]$ChannelId,
        [Parameter(Mandatory)][string]$Marker,
        [Parameter(Mandatory)][hashtable]$Headers
    )
    $Messages = @(Invoke-DiscordApi -Method GET -Path "/channels/$ChannelId/messages?limit=100" -Headers $Headers)
    return $Messages | Where-Object { $_.content -and $_.content.Contains($Marker) } | Select-Object -First 1
}

function Publish-Message {
    param(
        [Parameter(Mandatory)]$Channel,
        [Parameter(Mandatory)][string]$Content,
        [Parameter(Mandatory)][string]$Marker,
        [Parameter(Mandatory)][hashtable]$Headers,
        [Parameter(Mandatory)][string]$GuildId,
        [switch]$Pin
    )

    $Existing = Get-ExistingPublicationMessage -ChannelId $Channel.id -Marker $Marker -Headers $Headers
    if ($Existing) {
        Write-Host "[$($Channel.name)] Existing publication retained: $($Existing.id)" -ForegroundColor Cyan
        return [ordered]@{
            channel = $Channel.name
            channel_id = [string]$Channel.id
            message_id = [string]$Existing.id
            status = "existing"
            verified = $true
            pinned = [bool]$Existing.pinned
            url = "https://discord.com/channels/$GuildId/$($Channel.id)/$($Existing.id)"
        }
    }

    $Posted = Invoke-DiscordApi -Method POST -Path "/channels/$($Channel.id)/messages" -Headers $Headers -Body @{
        content = $Content
        allowed_mentions = @{ parse = @() }
    }

    $Verified = Invoke-DiscordApi -Method GET -Path "/channels/$($Channel.id)/messages/$($Posted.id)" -Headers $Headers
    if (-not $Verified.content.Contains($Marker)) {
        throw "Discord verification failed for message $($Posted.id) in #$($Channel.name)."
    }

    $Pinned = [bool]$Verified.pinned
    if ($Pin -and -not $Pinned) {
        try {
            $null = Invoke-DiscordApi -Method PUT -Path "/channels/$($Channel.id)/pins/$($Posted.id)" -Headers $Headers
            $Pinned = $true
        }
        catch {
            Write-Warning "Published message $($Posted.id), but pinning failed: $($_.Exception.Message)"
        }
    }

    Write-Host "[$($Channel.name)] Published and verified: $($Posted.id)" -ForegroundColor Green
    return [ordered]@{
        channel = $Channel.name
        channel_id = [string]$Channel.id
        message_id = [string]$Posted.id
        status = "published"
        verified = $true
        pinned = $Pinned
        url = "https://discord.com/channels/$GuildId/$($Channel.id)/$($Posted.id)"
    }
}

if (-not (Test-Path -LiteralPath $PublicationPath -PathType Leaf)) {
    throw "Publication payload not found: $PublicationPath"
}

$Payload = Get-Content -LiteralPath $PublicationPath -Raw -Encoding UTF8 | ConvertFrom-Json
$PayloadHash = Get-Sha256Hex -Path $PublicationPath
$ReportId = [string]$Payload.report_id
if (-not $ReportId) { throw "Publication payload does not define report_id." }

$ChannelNames = @($Payload.messages.PSObject.Properties.Name)
if ($ChannelNames.Count -eq 0) { throw "Publication payload contains no target channels." }

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host " GHOST ATLAS INSTITUTE · SERVERFORGE PUBLICATION" -ForegroundColor Cyan
Write-Host " Report:  $ReportId" -ForegroundColor White
Write-Host " Payload: $PayloadHash" -ForegroundColor DarkGray
Write-Host "============================================================" -ForegroundColor DarkCyan

if ($DryRun) {
    foreach ($ChannelName in $ChannelNames) {
        $Parts = @($Payload.messages.$ChannelName)
        for ($Index = 0; $Index -lt $Parts.Count; $Index++) {
            $Marker = "[$ReportId · $ChannelName · $($Index + 1)/$($Parts.Count)]"
            $Content = "$($Parts[$Index])`n`n$Marker"
            if ($Content.Length -gt 2000) {
                throw "Dry-run message exceeds Discord's 2000-character limit: #$ChannelName part $($Index + 1) ($($Content.Length) characters)."
            }
            Write-Host "DRY RUN #$ChannelName part $($Index + 1)/$($Parts.Count) · $($Content.Length) chars" -ForegroundColor Yellow
        }
    }
    Write-Host "Dry run complete. No Discord mutation occurred." -ForegroundColor Yellow
    exit 0
}

$Token = $env:DISCORD_BOT_TOKEN
$GuildId = $env:DISCORD_GUILD_ID
if (-not $Token) { throw "DISCORD_BOT_TOKEN is not present in Eden's local environment." }
if (-not $GuildId) { throw "DISCORD_GUILD_ID is not present in Eden's local environment." }
if (-not $ConfirmGuild) { throw "ConfirmGuild is required for live publication." }
if ([string]$ConfirmGuild -ne [string]$GuildId) {
    throw "Guild confirmation mismatch. No Discord mutation occurred."
}

$Headers = @{
    Authorization = "Bot $Token"
    "User-Agent" = "PROMETHEUS-ServerForge/1.1.1 (Ghost Atlas Institute Field Report)"
}

$Guild = Invoke-DiscordApi -Method GET -Path "/guilds/$GuildId" -Headers $Headers
if ($Guild.name -ne "PROMETHEUS Forge — Live Case Study") {
    throw "Authenticated guild name '$($Guild.name)' does not match the authorized PROMETHEUS case-study server."
}

$Channels = @(Invoke-DiscordApi -Method GET -Path "/guilds/$GuildId/channels" -Headers $Headers)
$PinChannels = @($Payload.pin_channels)
$Results = New-Object System.Collections.Generic.List[object]

foreach ($ChannelName in $ChannelNames) {
    $Channel = Get-ChannelByName -Channels $Channels -Name $ChannelName
    $Parts = @($Payload.messages.$ChannelName)
    for ($Index = 0; $Index -lt $Parts.Count; $Index++) {
        $Marker = "[$ReportId · $ChannelName · $($Index + 1)/$($Parts.Count)]"
        $Content = "$($Parts[$Index])`n`n$Marker"
        if ($Content.Length -gt 2000) {
            throw "Message exceeds Discord's 2000-character limit: #$ChannelName part $($Index + 1) ($($Content.Length) characters)."
        }
        $ShouldPin = (-not $NoPin) -and ($PinChannels -contains $ChannelName) -and ($Index -eq 0)
        $Result = Publish-Message -Channel $Channel -Content $Content -Marker $Marker -Headers $Headers -GuildId $GuildId -Pin:$ShouldPin
        $Results.Add([pscustomobject]$Result)
    }
}

New-Item -ItemType Directory -Path $ReceiptRoot -Force | Out-Null
$PublishedAt = [DateTime]::UtcNow.ToString("o")
$ReceiptPath = Join-Path $ReceiptRoot "$ReportId-discord-publication-receipt.json"
$Receipt = [ordered]@{
    schema = "serverforge.publication-receipt.v1"
    report_id = $ReportId
    publication_title = [string]$Payload.title
    published_at_utc = $PublishedAt
    publisher = "Prometheus Server Forge"
    guild_name = [string]$Guild.name
    guild_confirmation = "matched"
    payload_path = $Publication.Replace("\\", "/")
    payload_sha256 = $PayloadHash
    repository_head = Get-GitHead -WorkingDirectory $Root
    message_count = $Results.Count
    all_verified = -not (@($Results | Where-Object { -not $_.verified }).Count)
    secret_material_recorded = $false
    messages = @($Results)
}

[System.IO.File]::WriteAllText(
    $ReceiptPath,
    (($Receipt | ConvertTo-Json -Depth 20) + "`n"),
    $Utf8
)

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " SERVERFORGE CASE STUDY PUBLISHED AND VERIFIED" -ForegroundColor Green
Write-Host " Report:   $ReportId" -ForegroundColor Cyan
Write-Host " Messages: $($Results.Count)" -ForegroundColor Cyan
Write-Host " Receipt:  $ReceiptPath" -ForegroundColor Cyan
Write-Host " Token recorded: NO" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green

$Results | Format-Table channel, status, verified, pinned, message_id -AutoSize
