#Requires -Version 5.1
<#
.SYNOPSIS
  RealAI fully-local stack + self-heal + deepen loops (one command).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\realai\scripts\run_local_selfheal.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\realai\scripts\run_local_selfheal.ps1 -DiscoverMode all -DeepenLoops 3

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\realai\scripts\run_local_selfheal.ps1 -DeepenLoops 5 -ApplyPromote
#>

param(
  [int]$DeepenLoops = 3,
  [switch]$ApplyPromote,
  [switch]$SkipStart,
  [switch]$SkipHeal,
  [switch]$SkipDeepen,
  [string]$DiscoverMode = "desktop",
  [string]$Root = "C:\realai",
  [string]$Llama = "C:\llama-vulkan\llama-server.exe",
  [string]$Model = "C:\realai\models\qwen2.5-coder-7b-instruct-q5_k_m.gguf",
  [int]$OrchPort = 8001,
  [int]$VulkanPort = 8080
)

$ErrorActionPreference = "Continue"
$Logs = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
Set-Location $Root

# --- env (local-first) ---
$env:REALAI_VULKAN_BASE   = "http://127.0.0.1:$VulkanPort"
$env:REALAI_API_BASE      = "http://127.0.0.1:$OrchPort"
$env:NEXT_PUBLIC_API_URL  = "http://127.0.0.1:$OrchPort"
$env:REALAI_SELF_IMPROVE  = "true"
$env:ORCH_PORT            = "$OrchPort"
$env:REALAI_DEFAULT_MODEL = "realai-default-coder"
$env:REALAI_BACKEND_MODEL = "qwen2.5-coder-7b-instruct-q5_k_m.gguf"
$env:REALAI_TRAINING_DATA = "C:\realai\training\data"
$env:PYTHONPATH           = $Root
$env:PYTHONUNBUFFERED     = "1"

function Write-Step([string]$msg) {
  Write-Host ""
  Write-Host "==== $msg ====" -ForegroundColor Cyan
}

function Wait-Url([string]$url, [int]$tries = 60, [int]$sleepSec = 2) {
  for ($i = 0; $i -lt $tries; $i++) {
    try {
      $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
      if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { return $true }
    } catch {
      Start-Sleep -Seconds $sleepSec
    }
  }
  return $false
}

function Invoke-JsonPost([string]$url, $bodyObj) {
  $json = $bodyObj | ConvertTo-Json -Depth 8 -Compress
  return Invoke-RestMethod -Method Post -Uri $url -ContentType "application/json" -Body $json -TimeoutSec 3600
}

function Invoke-HealCli {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$HealArgs)
  $cli = Join-Path $Root "scripts\heal_cli.py"
  & $script:py $cli @HealArgs
  return $LASTEXITCODE
}

$script:py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $script:py) { $script:py = "python" }

$applyFlag = @()
if ($ApplyPromote) { $applyFlag = @("--apply") }

# ---------------------------------------------------------------------------
# 1) START STACK
# ---------------------------------------------------------------------------
if (-not $SkipStart) {
  Write-Step "Start local stack (Vulkan :$VulkanPort + orch :$OrchPort)"

  foreach ($port in @($VulkanPort, $OrchPort)) {
    Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
      ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
  }
  Start-Sleep -Seconds 1

  if (-not (Test-Path $Llama)) { throw "Missing llama-server: $Llama" }
  if (-not (Test-Path $Model)) { throw "Missing GGUF model: $Model" }

  $vArgs = @(
    "-m", $Model,
    "--host", "0.0.0.0",
    "--port", "$VulkanPort",
    "-c", "8192",
    "-ngl", "99",
    "--jinja"
  )
  Start-Process -FilePath $Llama -ArgumentList $vArgs -WorkingDirectory "C:\llama-vulkan" `
    -RedirectStandardOutput (Join-Path $Logs "vulkan.out.log") `
    -RedirectStandardError  (Join-Path $Logs "vulkan.err.log") `
    -WindowStyle Hidden
  Write-Host "Started llama-server (Vulkan) - loading model may take 1-3 min..."

  if (Wait-Url "http://127.0.0.1:$VulkanPort/health" 90 2) {
    Write-Host "Vulkan healthy" -ForegroundColor Green
  } else {
    Write-Host "WARNING: Vulkan not healthy yet - orch will start degraded. See logs\vulkan.err.log" -ForegroundColor Yellow
  }

  Start-Process -FilePath $script:py -ArgumentList @(
    "-m", "realai.v3_orchestrator",
    "--host", "127.0.0.1",
    "--port", "$OrchPort"
  ) -WorkingDirectory $Root `
    -RedirectStandardOutput (Join-Path $Logs "v3-orchestrator.out.log") `
    -RedirectStandardError  (Join-Path $Logs "v3-orchestrator.err.log") `
    -WindowStyle Hidden
  Write-Host "Started v3 orchestrator on :$OrchPort"

  if (Wait-Url "http://127.0.0.1:$OrchPort/health" 30 1) {
    try {
      $h = Invoke-RestMethod "http://127.0.0.1:$OrchPort/health"
      Write-Host ("Orchestrator: status={0} vulkan.ok={1}" -f $h.status, $h.vulkan.ok) -ForegroundColor Green
    } catch {
      Write-Host "Orchestrator answered but health parse failed" -ForegroundColor Yellow
    }
  } else {
    Write-Host "WARNING: orchestrator not answering. See logs\v3-orchestrator.err.log" -ForegroundColor Yellow
  }
}

$base = "http://127.0.0.1:$OrchPort"

# ---------------------------------------------------------------------------
# 2) SELF-HEAL LOOP
# ---------------------------------------------------------------------------
if (-not $SkipHeal) {
  Write-Step "Self-heal: learn keywords"
  try {
    $null = Invoke-JsonPost "$base/v1/self-heal/learn-keywords" @{}
    Write-Host "learn-keywords OK (API)"
  } catch {
    Write-Host "API learn failed, CLI fallback: $_"
    Invoke-HealCli learn | Out-Host
  }

  Write-Step "Self-heal: discover mode=$DiscoverMode"
  try {
    $disc = Invoke-JsonPost "$base/v1/self-heal/discover" @{ mode = $DiscoverMode }
    Write-Host ("discover ok={0}" -f $disc.ok)
  } catch {
    Write-Host "API discover failed, CLI fallback: $_"
    Invoke-HealCli discover $DiscoverMode | Out-Host
  }

  Write-Step "Self-heal: assemble gold index + promote_queue"
  try {
    $asm = Invoke-JsonPost "$base/v1/self-heal/assemble" @{}
    Write-Host ("assemble ok={0}" -f $asm.ok)
  } catch {
    Write-Host "API assemble failed, CLI fallback: $_"
    Invoke-HealCli assemble | Out-Host
  }

  Write-Step ("Self-heal: promote apply={0}" -f [bool]$ApplyPromote)
  try {
    $prom = Invoke-JsonPost "$base/v1/self-heal/promote" @{ apply = [bool]$ApplyPromote }
    Write-Host ("promote ok={0} apply={1}" -f $prom.ok, [bool]$ApplyPromote)
  } catch {
    Write-Host "API promote failed, CLI fallback: $_"
    if ($ApplyPromote) {
      Invoke-HealCli promote --apply | Out-Host
    } else {
      Invoke-HealCli promote | Out-Host
    }
  }

  Write-Step "Self-heal: full cycle"
  try {
    $cyc = Invoke-JsonPost "$base/v1/self-heal/cycle" @{ apply = [bool]$ApplyPromote }
    Write-Host ("cycle completed (keys={0})" -f (($cyc | Get-Member -MemberType NoteProperty).Count))
  } catch {
    Write-Host "API cycle failed, CLI fallback: $_"
    if ($ApplyPromote) {
      Invoke-HealCli cycle --apply | Out-Host
    } else {
      Invoke-HealCli cycle | Out-Host
    }
  }
}

# ---------------------------------------------------------------------------
# 3) DEEPEN LOOPS
# ---------------------------------------------------------------------------
if ((-not $SkipDeepen) -and ($DeepenLoops -gt 0)) {
  Write-Step "Deepen loops x $DeepenLoops"
  for ($i = 1; $i -le $DeepenLoops; $i++) {
    Write-Host "--- deepen $i / $DeepenLoops ---" -ForegroundColor Yellow
    try {
      $d = Invoke-JsonPost "$base/v1/deepen" @{
        assemble = $true
        hive     = $true
        cycle    = $true
      }
      Write-Host ("  deeper={0} score {1} -> {2} success={3}" -f $d.deeper, $d.before_score, $d.after_score, $d.success)
    } catch {
      Write-Host "  API deepen failed, CLI: $_"
      Invoke-HealCli deepen | Out-Host
    }
  }
}

# ---------------------------------------------------------------------------
# 4) STATUS SNAPSHOT
# ---------------------------------------------------------------------------
Write-Step "Status snapshot"
try {
  $h = Invoke-RestMethod "$base/health"
  Write-Host ("health: {0}  vulkan: {1}" -f $h.status, $h.vulkan.ok)
} catch {
  Write-Host "health: FAIL $_"
}

try {
  $c = Invoke-RestMethod "$base/v1/capabilities"
  Write-Host ("capabilities weighted_pct: {0}" -f $c.weighted_pct)
  if ($null -ne $c.by_status) {
    Write-Host ("  by_status: LIVE={0} PARTIAL={1} GOLD={2}" -f $c.by_status.LIVE, $c.by_status.PARTIAL, $c.by_status.GOLD)
  }
} catch {
  Write-Host "capabilities: FAIL"
}

try {
  $r = Invoke-RestMethod "$base/v1/recovery"
  Write-Host ("recovery: modules {0}/{1}  lora={2}" -f $r.live_modules_ready, $r.live_modules_total, $r.lora_adapter_count)
} catch {
  Write-Host "recovery: FAIL"
}

try {
  $s = Invoke-RestMethod "$base/v1/self-heal/status"
  Write-Host ("self-heal enabled={0} promote_queue={1}" -f $s.enabled, $s.promote_queue_items)
} catch {
  Write-Host "self-heal status: FAIL"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " RealAI local stack"
Write-Host "   API / UI base : http://127.0.0.1:$OrchPort"
Write-Host "   Vulkan        : http://127.0.0.1:$VulkanPort"
Write-Host "   Chat model    : realai-default-coder"
Write-Host "   Logs          : $Logs"
Write-Host "   Deepen report : $Root\scan_results\deepen_last.md"
Write-Host "   Self-heal     : $Root\scan_results\self_heal_last_cycle.md"
Write-Host "   Desktop gold  : $Root\scan_results\desktop_missing_gold_map.md"
Write-Host ""
Write-Host " Quick tests:"
Write-Host "   curl http://127.0.0.1:$OrchPort/health"
Write-Host "   curl http://127.0.0.1:$OrchPort/v1/models"
Write-Host "============================================================" -ForegroundColor Green
