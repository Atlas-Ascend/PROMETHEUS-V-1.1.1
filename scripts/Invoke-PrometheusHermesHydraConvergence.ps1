#requires -Version 5.1
#requires -RunAsAdministrator

[CmdletBinding()]
param(
    [string]$Repo = "C:\Ghost\PROMETHEUS-AIS-V-1.1.1",
    [string]$Branch = "prometheus/hermes-agent-zero-command-to-proof",
    [string]$Model = "hermes3:8b",
    [string]$EdenModel = "prometheus-hermes:latest",
    [int]$AgentZeroPort = 5080,
    [int]$MaxHydraCycles = 12
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$EvidenceRoot = Join-Path $Repo "evidence\hermes-agent-zero-hydra\$Stamp"
$RuntimeRoot = Join-Path $Repo ".prometheus-runtime"
$OfficeRoot = Join-Path $Repo "workforce_spine\office_200"
$PromptPath = Join-Path $RuntimeRoot "PROMETHEUS_COMMAND_TO_PROOF.md"
$AgentPath = Join-Path $RuntimeRoot "prometheus_hermes_agent.py"
$StatePath = Join-Path $RuntimeRoot "hydra-state.json"
$OllamaApi = "http://127.0.0.1:11434"

function Gate([string]$Text, [ConsoleColor]$Color = [ConsoleColor]::Cyan) {
    Write-Host ""
    Write-Host ("=" * 78) -ForegroundColor $Color
    Write-Host " $Text" -ForegroundColor $Color
    Write-Host ("=" * 78) -ForegroundColor $Color
}

function Write-Utf8([string]$Path, [string]$Content) {
    $parent = Split-Path -Parent $Path
    if ($parent) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    [IO.File]::WriteAllText($Path, $Content, [Text.UTF8Encoding]::new($false))
}

function Run([string]$File, [string[]]$Args, [switch]$AllowFailure) {
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $lines = @(& $File @Args 2>&1 | ForEach-Object { $_.ToString() })
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $old }
    $lines | ForEach-Object { Write-Host $_ }
    if (-not $AllowFailure -and $code -ne 0) {
        throw "Command failed ($code): $File $($Args -join ' ')"
    }
    [pscustomobject]@{ ExitCode = $code; Output = ($lines -join "`n") }
}

function Test-Http([string]$Url) {
    try { Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5 | Out-Null; $true }
    catch { $false }
}

Gate "PROMETHEUS Ω | HERMES + AGENT ZERO + HYDRA CONVERGENCE" Magenta

if (-not (Test-Path $Repo)) {
    $alt = "C:\Ghost\PROMETHEUS-V-1.1.1"
    if (Test-Path $alt) { $Repo = $alt } else { throw "PROMETHEUS repository not found." }
}

New-Item -ItemType Directory -Path $EvidenceRoot,$RuntimeRoot,$OfficeRoot -Force | Out-Null
Set-Location $Repo

if ((git rev-parse --is-inside-work-tree 2>$null) -ne "true") { throw "Not a Git worktree: $Repo" }

Gate "GATE I | THOTH BRANCH AND LINEAGE"

git add -A
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) { git commit -m "checkpoint: preserve state before Hermes HYDRA convergence" }

git fetch origin --prune
if ((git branch --list $Branch).Trim()) {
    git checkout $Branch
} elseif ((git branch -r --list "origin/$Branch").Trim()) {
    git checkout -b $Branch --track "origin/$Branch"
} else {
    git checkout -b $Branch
}

git pull --rebase origin $Branch
$Baseline = (git rev-parse HEAD).Trim()
Write-Host "[BASELINE] $Baseline" -ForegroundColor Green

Gate "GATE II | WORKFORCE SPINE 200-ROLE OFFICE"

$divisions = [ordered]@{
    "JANUS_ODIN" = @("Canon Recon Lead","Branch Truth Analyst","Requirement Cartographer","Dependency Sequencer","Contradiction Examiner","Acceptance Matrix Steward","Next-Task Governor","Scope Boundary Officer","Human Gate Liaison","Build Truth Registrar")
    "PACKET_OS" = @("Mission Packet Architect","Task Decomposer","Evidence Contract Author","Constraint Encoder","Rollback Packet Author","Budget Packet Analyst","Checkpoint Packet Author","Dependency Packet Router","Completion Gate Author","Packet Integrity Auditor")
    "WORKFORCE_SPINE" = @("Role Activation Director","Work Packet Dispatcher","Capacity Planner","Specialist Matcher","Queue Steward","Escalation Router","Cross-Squad Coordinator","Idle-Lane Reallocator","Office Telemetry Analyst","Institutional Map Curator")
    "METAFORGE" = @("Minimal Patch Architect","Structural Repair Architect","Adapter Isolation Architect","Novelty Scoring Scientist","Candidate Diversity Auditor","Mutation Planner","Surrogate Test Designer","Route Pruning Analyst","Workspace Blueprint Author","Evolution Budget Steward")
    "EDEN_CALI" = @("Windows Runtime Operator","Linux Runtime Operator","Filesystem Executor","Process Supervisor","Artifact Collector","Environment Profiler","Conversational Mission Steward","Operator Status Narrator","Human Checkpoint Coordinator","Local Tool Boundary Auditor")
    "HERMES" = @("Resident Coding Intelligence","Repository Interpreter","Implementation Planner","Patch Generator","Test Repair Agent","Context Compressor","Tool Selection Agent","Local Model Performance Analyst","Prompt Contract Steward","Hermes Health Examiner")
    "AGENT_ZERO" = @("Container Agent Operator","Project Workspace Steward","Subagent Coordinator","Docker Boundary Auditor","Model Provider Configurator","Agent Memory Curator","Agent Skill Integrator","Host Connector Steward","Agent Zero Recovery Operator","Interactive Office Liaison")
    "HEPHAESTUS" = @("Command Execution Engineer","Build Engineer","Packaging Engineer","Installer Engineer","Subprocess Evidence Recorder","Artifact Hash Engineer","Benchmark Runner","Environment Reproducer","Uninstall Verification Engineer","Release Forge Operator")
    "HYDRA_UNO" = @("Continuity Governor","Checkpoint Engineer","Replay Protection Engineer","Failover Router","Runtime Health Monitor","Backoff Controller","Crash Recovery Engineer","Duplicate Execution Sentinel","Rollback Coordinator","Resume Proof Auditor")
    "ADVERSARIAL_TWIN" = @("Replay Attack Designer","Malformed Input Challenger","Permission Boundary Challenger","Dependency Saboteur","Race Condition Challenger","Evidence Corruption Challenger","Prompt Injection Challenger","Rollback Failure Challenger","Hidden State Challenger","Future Failure Analyst")
    "SECA_DEVOS" = @("Promotion Arbiter","Regression Judge","Security Evidence Judge","Maintainability Judge","Rollback Readiness Judge","Runtime Continuity Judge","Claim Confidence Judge","Unsupported Finding Rejector","Repair Mandate Officer","Release Gate Authority")
    "PROOFGRID" = @("Receipt Schema Engineer","JSON Receipt Compiler","Markdown Receipt Compiler","Hash Manifest Engineer","Evidence Reference Verifier","Tamper Detection Engineer","Claim Support Mapper","Dashboard State Projector","Proof Bundle Assembler","Receipt Verification Auditor")
    "THOTH_CANON" = @("Lineage Archivist","Commit Chronologist","Candidate History Curator","Decision Record Steward","Evidence Retention Officer","Canon Version Custodian","Session Reference Archivist","Release Chronicle Author","Provenance Graph Engineer","Archive Integrity Auditor")
    "CAPABILITY_GENOME" = @("Genome Compiler","Problem Signature Analyst","Reuse Condition Author","Exclusion Condition Author","Failed Route Curator","Successful Motif Curator","Transfer Test Engineer","Genome Matcher","Genome Mutation Auditor","Confidence Boundary Author")
    "MEDUSA" = @("Secret Scanner","Credential Exposure Auditor","Private Path Scrubber","Unsupported Claim Hunter","Debug Artifact Examiner","Webhook Sanitizer","Permission Hardening Analyst","Public Private Boundary Steward","Reverse Verification Analyst","Release Disclosure Auditor")
    "ARIADNE" = @("Clean Clone Engineer","Judge Path Navigator","Hidden State Detector","Deterministic Demo Engineer","Installation Reproducer","Cross-Platform Launcher Engineer","Demo Timing Analyst","Artifact Index Author","Submission Rehearsal Operator","Clean Room Proof Auditor")
    "SERVERFORGE" = @("Structured Event Engineer","Discord Transport Steward","Sanitization Officer","Build Observatory Analyst","Case Study Assembler","Screenshot Evidence Curator","Submission Chronology Author","Event Schema Auditor","External Consequence Monitor","Public Proof Publisher")
    "OLYMPIAN_CONSOLE" = @("Mission State Designer","Candidate Arena Designer","Runtime Head Visualizer","Promotion Gate Visualizer","Receipt Viewer Engineer","Genome Viewer Engineer","Operator Console Tester","Truth Consistency Auditor","Judge Experience Designer","Final Verdict Presenter")
    "ROADBRIDGE_CROWNGRID" = @("Mobile Transport Engineer","Tailscale Route Steward","SSH Boundary Engineer","Remote Command Broker","Operator Authority Auditor","Device Identity Steward","Command Guard Designer","Receipt Return Engineer","Field Continuity Operator","Access Revocation Officer")
    "GARI_AIS_OMEGA" = @("Resource Budget Analyst","Compute Allocation Planner","Information Gain Analyst","Risk Budget Steward","Recursive Mission Designer","Self-Build Scope Auditor","Protected Path Steward","Promotion Experiment Analyst","Second-Repository Test Planner","Economic Proof Analyst")
}

$roles = @()
$seq = 0
foreach ($division in $divisions.Keys) {
    foreach ($title in $divisions[$division]) {
        $seq++
        $roles += [ordered]@{
            role_id = "PROM-ROLE-{0:D3}" -f $seq
            division = $division
            title = $title
            activation = "ON_DEMAND"
            authority = if ($division -eq "SECA_DEVOS") { "PROMOTION" } else { "IMPLEMENTATION_OR_ADVISORY" }
            produces = @("inspectable_work_packet","evidence_references","completion_state")
            law = "No role may claim completion without executable evidence."
        }
    }
}
if ($roles.Count -ne 200) { throw "Role generation failed: $($roles.Count)" }
$roles | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $OfficeRoot "office.json") -Encoding UTF8
$roles | Export-Csv (Join-Path $OfficeRoot "office.csv") -NoTypeInformation
Write-Utf8 (Join-Path $OfficeRoot "README.md") "# PROMETHEUS 200-Role Institutional Office`n`nExactly 200 on-demand capability roles across 20 existing-organ divisions. This is an institutional capability map, not a claim of 200 simultaneous autonomous developers.`n"
Write-Host "[PROVEN] 200 roles generated" -ForegroundColor Green

Gate "GATE III | OLLAMA + HERMES"

$ollama = Get-Command ollama.exe -ErrorAction SilentlyContinue
if (-not $ollama) {
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) { throw "winget is required to install Ollama." }
    Run winget.exe @("install","--id","Ollama.Ollama","--exact","--accept-source-agreements","--accept-package-agreements") | Out-Null
    $env:Path += ";$env:LOCALAPPDATA\Programs\Ollama"
    $ollama = Get-Command ollama.exe -ErrorAction Stop
}

if (-not (Test-Http "$OllamaApi/api/tags")) {
    Start-Process -FilePath $ollama.Source -ArgumentList "serve" -WindowStyle Hidden
    1..60 | ForEach-Object { if (Test-Http "$OllamaApi/api/tags") { return }; Start-Sleep 2 }
}
if (-not (Test-Http "$OllamaApi/api/tags")) { throw "Ollama API did not start." }

Run $ollama.Source @("pull",$Model) | Out-Null
$modelfile = Join-Path $RuntimeRoot "Hermes.Modelfile"
Write-Utf8 $modelfile @"
FROM $Model
PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_ctx 16384
SYSTEM You are HERMES, EDEN's resident coding intelligence. PROMETHEUS is the governing Command-to-Proof authority. Inspect before changing. Implement before explaining. Run tests. Challenge success. Repair failures. Preserve receipts and lineage. Continue to the next task. Never invent proof.
"@
Run $ollama.Source @("create",$EdenModel,"-f",$modelfile) | Out-Null

$probe = @{ model=$EdenModel; stream=$false; messages=@(@{role="user";content="Reply exactly HERMES_ONLINE"}) } | ConvertTo-Json -Depth 8
$probeResult = Invoke-RestMethod -Uri "$OllamaApi/api/chat" -Method Post -ContentType "application/json" -Body $probe -TimeoutSec 600
if ([string]$probeResult.message.content -notmatch "HERMES_ONLINE") { throw "Hermes probe failed." }
Write-Host "[PROVEN] HERMES_ONLINE" -ForegroundColor Green

Gate "GATE IV | AGENT ZERO"

$AgentZeroState = "UNAVAILABLE"
if (Get-Command docker.exe -ErrorAction SilentlyContinue) {
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        docker rm -f prometheus-agent-zero *> $null
        $dockerArgs = @(
            "run","-d","--name","prometheus-agent-zero","--restart","unless-stopped",
            "-p","${AgentZeroPort}:80",
            "--add-host","host.docker.internal:host-gateway",
            "-v","prometheus_a0_usr:/a0/usr",
            "-v","${Repo}:/a0/usr/projects/PROMETHEUS",
            "-e","A0_SET_chat_model_provider=ollama",
            "-e","A0_SET_chat_model_name=$EdenModel",
            "-e","A0_SET_chat_model_api_base=http://host.docker.internal:11434",
            "-e","A0_SET_utility_model_provider=ollama",
            "-e","A0_SET_utility_model_name=$EdenModel",
            "-e","A0_SET_utility_model_api_base=http://host.docker.internal:11434",
            "agent0ai/agent-zero"
        )
        Run docker.exe $dockerArgs | Out-Null
        $AgentZeroState = "RUNNING"
    }
}
Write-Host "[STATE] Agent Zero: $AgentZeroState on http://127.0.0.1:$AgentZeroPort" -ForegroundColor Cyan

Gate "GATE V | PROMETHEUS GOVERNING PROMPT"

$prompt = @"
# PROMETHEUS Ω HERMES AGENT ZERO HYDRA COMMAND-TO-PROOF

Follow build_truth/00_CANON_LOCK.md, 01_GHOST_ATLAS_GRAND_SLAM.md, 02_BUILD_TRUTH.md, and 03_HERMES_AGENT_ZERO_HYDRA_CONVERGENCE.md.

Operate through existing organs only. No replacement build. No new product identity.

Continuous law: inspect current Git and Build Truth; select the highest-priority unproven contest obligation; activate relevant roles from workforce_spine/office_200/office.json; create at least three materially distinct candidates when implementation alternatives are required; execute real commands; preserve stdout, stderr, exit code, duration, hashes, workspaces, and rollback; reject weak candidates with evidence; challenge the provisional leader independently; let SECA block promotion for severe findings; repair; retest; issue ProofGrid receipts; update Build Truth; commit; continue.

Required closure: mission validation; route novelty; isolated candidates; real execution; two different rejections; provisional winner; HYDRA checkpoint and resume event; replay defect discovery; blocked promotion; repair; verified receipt; capability genome; recursive self-build; second-task genome reuse; ServerForge case study; Olympian truthful state; package build; clean install; doctor; demo; rollback; uninstall; reinstall; clean-room reproduction; final release receipt and submission package.

Never mark PROVEN from prose, a step budget, or a single passing run. Continue every unblocked task. Stop only for a concrete external credential, physical resource, irreversible human decision, or unavailable external service.
"@
Write-Utf8 $PromptPath $prompt

Gate "GATE VI | HERMES TOOL AGENT"

$agent = @'
from __future__ import annotations
import argparse, datetime as dt, json, os, pathlib, subprocess, time, urllib.request

LIMIT=14000

def cut(s):
    s=str(s)
    return s if len(s)<=LIMIT else s[:LIMIT//2]+"\n...[preserved in full log]...\n"+s[-LIMIT//2:]

def api(url,payload):
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=1800) as r: return json.loads(r.read().decode())

class Agent:
    def __init__(self,a):
        self.repo=pathlib.Path(a.repo).resolve(); self.api=a.api.rstrip('/'); self.model=a.model
        self.prompt=pathlib.Path(a.prompt).read_text(encoding='utf-8'); self.ev=pathlib.Path(a.evidence)
        self.ev.mkdir(parents=True,exist_ok=True); (self.ev/'commands').mkdir(exist_ok=True); self.n=0
    def safe(self,p):
        x=(self.repo/p).resolve()
        if os.path.commonpath([str(self.repo),str(x)])!=str(self.repo): raise ValueError('path escape')
        return x
    def tools(self):
        return [
          {"type":"function","function":{"name":"list_files","description":"List repository files","parameters":{"type":"object","properties":{"path":{"type":"string"}}}}},
          {"type":"function","function":{"name":"read_file","description":"Read repository file","parameters":{"type":"object","required":["path"],"properties":{"path":{"type":"string"}}}}},
          {"type":"function","function":{"name":"write_file","description":"Write repository text file","parameters":{"type":"object","required":["path","content"],"properties":{"path":{"type":"string"},"content":{"type":"string"}}}}},
          {"type":"function","function":{"name":"run","description":"Run PowerShell in repository for implementation, tests, builds, proof, and Git","parameters":{"type":"object","required":["command"],"properties":{"command":{"type":"string"},"timeout":{"type":"integer"}}}}},
          {"type":"function","function":{"name":"finish","description":"Close cycle only as PROVEN PARTIAL or BLOCKED","parameters":{"type":"object","required":["status","summary"],"properties":{"status":{"type":"string"},"summary":{"type":"string"}}}}}
        ]
    def call(self,name,a):
        if name=='list_files':
            root=self.safe(a.get('path','.')); return {'entries':[str(x.relative_to(self.repo)) for x in list(root.rglob('*'))[:700]]}
        if name=='read_file': return {'content':cut(self.safe(a['path']).read_text(encoding='utf-8',errors='replace'))}
        if name=='write_file':
            p=self.safe(a['path']); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(a['content'],encoding='utf-8'); return {'ok':True,'path':str(p.relative_to(self.repo))}
        if name=='run':
            cmd=a['command']; low=cmd.lower()
            for bad in ['format ','diskpart','git push --force','git reset --hard','remove-item c:\\']:
                if bad in low: return {'ok':False,'blocked':bad}
            self.n+=1; d=self.ev/'commands'; start=time.time()
            try:
                r=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',cmd],cwd=self.repo,text=True,capture_output=True,timeout=min(int(a.get('timeout',900)),1800))
                code=r.returncode; out=r.stdout; err=r.stderr
            except subprocess.TimeoutExpired as e: code=124; out=e.stdout or ''; err=e.stderr or ''
            (d/f'{self.n:04d}-stdout.log').write_text(out,encoding='utf-8'); (d/f'{self.n:04d}-stderr.log').write_text(err,encoding='utf-8')
            return {'ok':code==0,'exit_code':code,'seconds':round(time.time()-start,2),'stdout':cut(out),'stderr':cut(err)}
        if name=='finish': return {'finish':True,**a}
        return {'error':'unknown tool'}
    def go(self,steps):
        msgs=[{'role':'system','content':'You are Hermes operating under PROMETHEUS Command-to-Proof. Use tools to act, test, challenge, repair, receipt, commit, and continue.'},{'role':'user','content':self.prompt}]
        final={'status':'PARTIAL','summary':'step budget reached'}
        for step in range(1,steps+1):
            res=api(self.api+'/api/chat',{'model':self.model,'stream':False,'messages':msgs,'tools':self.tools(),'options':{'temperature':0.1,'num_ctx':16384}})
            m=res.get('message',{}); msgs.append(m)
            with (self.ev/'transcript.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps({'step':step,'response':res})+'\n')
            calls=m.get('tool_calls') or []
            if not calls:
                msgs.append({'role':'user','content':'Continue with a real tool. Do the next unproven task now.'}); continue
            for c in calls:
                fn=c.get('function',{}); args=fn.get('arguments',{})
                if isinstance(args,str):
                    try: args=json.loads(args)
                    except: args={}
                result=self.call(fn.get('name',''),args)
                msgs.append({'role':'tool','tool_name':fn.get('name',''),'content':cut(json.dumps(result))})
                if result.get('finish'):
                    final={'status':result.get('status','PARTIAL').upper(),'summary':result.get('summary','')}
                    (self.ev/'final-state.json').write_text(json.dumps(final,indent=2),encoding='utf-8'); return final
            if len(msgs)>70: msgs=msgs[:2]+msgs[-50:]
        (self.ev/'final-state.json').write_text(json.dumps(final,indent=2),encoding='utf-8'); return final

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--repo'); p.add_argument('--api'); p.add_argument('--model'); p.add_argument('--prompt'); p.add_argument('--evidence'); p.add_argument('--steps',type=int,default=80)
    a=p.parse_args(); print(json.dumps(Agent(a).go(a.steps),indent=2))
'@
Write-Utf8 $AgentPath $agent

Gate "GATE VII | HYDRA AUTONOMOUS REPAIR LOOP" Magenta

$python = if (Get-Command py.exe -ErrorAction SilentlyContinue) { @("py.exe","-3") } elseif (Get-Command python.exe -ErrorAction SilentlyContinue) { @("python.exe") } else { throw "Python is required." }
$CampaignState = "PARTIAL"

for ($cycle=1; $cycle -le $MaxHydraCycles; $cycle++) {
    $cycleRoot = Join-Path $EvidenceRoot ("cycle-{0:D2}" -f $cycle)
    New-Item -ItemType Directory -Path $cycleRoot -Force | Out-Null
    $state = [ordered]@{ cycle=$cycle; started=(Get-Date).ToString("o"); baseline=(git rev-parse HEAD).Trim(); model=$EdenModel; agent_zero=$AgentZeroState }
    $state | ConvertTo-Json | Set-Content $StatePath -Encoding UTF8

    if (-not (Test-Http "$OllamaApi/api/tags")) {
        Start-Process -FilePath $ollama.Source -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep 5
    }
    if ($AgentZeroState -eq "RUNNING") { docker start prometheus-agent-zero *> $null }

    & $python[0] @($python[1..($python.Count-1)]) $AgentPath --repo $Repo --api $OllamaApi --model $EdenModel --prompt $PromptPath --evidence $cycleRoot --steps 80
    $agentExit = $LASTEXITCODE

    Set-Location $Repo
    $testLog = Join-Path $cycleRoot "regression.log"
    if (Test-Path "pyproject.toml") {
        & $python[0] @($python[1..($python.Count-1)]) -m pytest -q *> $testLog
        $testExit = $LASTEXITCODE
    } else { "No pyproject.toml" | Set-Content $testLog; $testExit = 78 }

    git add -A
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) { git commit -m "prometheus: HYDRA cycle $cycle convergence" }

    $finalFile = Join-Path $cycleRoot "final-state.json"
    if (Test-Path $finalFile) { $CampaignState = (Get-Content $finalFile -Raw | ConvertFrom-Json).status }
    if ($testExit -ne 0 -and $CampaignState -eq "PROVEN") { $CampaignState = "PARTIAL" }

    [ordered]@{ cycle=$cycle; agent_exit=$agentExit; test_exit=$testExit; state=$CampaignState; commit=(git rev-parse HEAD).Trim(); finished=(Get-Date).ToString("o") } | ConvertTo-Json | Set-Content (Join-Path $cycleRoot "hydra-receipt.json") -Encoding UTF8

    if ($CampaignState -eq "PROVEN" -and $testExit -eq 0) { break }
    if ($CampaignState -eq "BLOCKED") { break }
    Start-Sleep ([Math]::Min(30, 2 * $cycle))
}

Gate "GATE VIII | PROOFGRID RELEASE PRESERVATION"

git add -A
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) { git commit -m "proof: preserve Hermes Agent Zero HYDRA convergence" }
$FinalCommit = (git rev-parse HEAD).Trim()
$Tag = "prometheus-hermes-hydra-$($CampaignState.ToLower())-$Stamp"
git tag -a $Tag -m "PROMETHEUS Hermes Agent Zero HYDRA state $CampaignState"
$PushState = "LOCAL_ONLY"
git push -u origin $Branch
if ($LASTEXITCODE -eq 0) { git push origin $Tag; if ($LASTEXITCODE -eq 0) { $PushState = "PUBLISHED" } }

$receipt = [ordered]@{
    campaign="PROMETHEUS Hermes Agent Zero HYDRA Command-to-Proof"
    status=$CampaignState
    baseline=$Baseline
    final_commit=$FinalCommit
    branch=$Branch
    tag=$Tag
    publication=$PushState
    hermes_model=$EdenModel
    ollama_api=$OllamaApi
    agent_zero=$AgentZeroState
    agent_zero_url="http://127.0.0.1:$AgentZeroPort"
    office_roles=200
    evidence=$EvidenceRoot
    timestamp=(Get-Date).ToString("o")
}
$receipt | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $EvidenceRoot "FINAL_RECEIPT.json") -Encoding UTF8

Gate "GATE Ω | CONVERGENCE COMPLETE" $(if ($CampaignState -eq "PROVEN") {[ConsoleColor]::Green} else {[ConsoleColor]::Yellow})
Write-Host "State:       $CampaignState" -ForegroundColor Cyan
Write-Host "Branch:      $Branch" -ForegroundColor Cyan
Write-Host "Commit:      $FinalCommit" -ForegroundColor Cyan
Write-Host "Tag:         $Tag" -ForegroundColor Cyan
Write-Host "Publication: $PushState" -ForegroundColor Cyan
Write-Host "Hermes:      $EdenModel" -ForegroundColor Cyan
Write-Host "Agent Zero:  $AgentZeroState at http://127.0.0.1:$AgentZeroPort" -ForegroundColor Cyan
Write-Host "Evidence:    $EvidenceRoot" -ForegroundColor Cyan
