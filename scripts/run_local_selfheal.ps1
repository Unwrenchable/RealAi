#Requires -Version 5.1
<#
.SYNOPSIS
  RealAI-clean local: start stack + CURATED PROMOTE APPLY + verify.
  Does NOT dump more scan folders by default.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\RealAI-clean\scripts\run_local_selfheal.ps1

.EXAMPLE
  # Promote only (stack already up)
  powershell -ExecutionPolicy Bypass -File C:\RealAI-clean\scripts\run_local_selfheal.ps1 -SkipStart

.EXAMPLE
  # Also run deepen loops after promote
  powershell -ExecutionPolicy Bypass -File C:\RealAI-clean\scripts\run_local_selfheal.ps1 -DeepenLoops 2
#>

param(
  [int]$DeepenLoops = 0,
  [switch]$SkipStart,
  [switch]$SkipPromote,
  [switch]$Force,
  [switch]$Scan,  # optional: only if you really want discover (makes mess)
  [string]$Root = "C:\RealAI-clean",
  [string]$Llama = "C:\llama-vulkan\llama-server.exe",
  [string]$Model = "C:\RealAI-clean\models\qwen2.5-coder-7b-instruct-q5_k_m.gguf",
  [int]$OrchPort = 8001,
  [int]$VulkanPort = 8080
)

$ErrorActionPreference = "Continue"
$Logs = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root "scan_results") | Out-Null
Set-Location $Root

$env:REALAI_VULKAN_BASE   = "http://127.0.0.1:$VulkanPort"
$env:REALAI_API_BASE      = "http://127.0.0.1:$OrchPort"
$env:NEXT_PUBLIC_API_URL  = "http://127.0.0.1:$OrchPort"
$env:REALAI_SELF_IMPROVE  = "true"
$env:ORCH_PORT            = "$OrchPort"
$env:REALAI_DEFAULT_MODEL = "realai-default-coder"
$env:REALAI_BACKEND_MODEL = "qwen2.5-coder-7b-instruct-q5_k_m.gguf"
$env:REALAI_TRAINING_DATA = Join-Path $Root "training\data"
$env:PYTHONPATH           = $Root
$env:PYTHONUNBUFFERED     = "1"
if (-not $env:REALAI_API_KEY) { $env:REALAI_API_KEY = "local" }

function Write-Step([string]$msg) {
  Write-Host ""
  Write-Host "==== $msg ====" -ForegroundColor Cyan
}

function Wait-Url([string]$url, [int]$tries = 60, [int]$sleepSec = 2) {
  for ($i = 0; $i -lt $tries; $i++) {
    try {
      $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
      if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { return $true }
    } catch { Start-Sleep -Seconds $sleepSec }
  }
  return $false
}

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "python" }

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
  if (-not (Test-Path $Model)) {
    $fallback = "C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf"
    if (Test-Path $fallback) {
      Write-Host "GGUF not at $Model - using fallback $fallback" -ForegroundColor Yellow
      $Model = $fallback
    } else {
      throw "Missing GGUF: $Model (also missing fallback: $fallback)"
    }
  }

  $vArgs = @(
    "-m", $Model, "--host", "0.0.0.0", "--port", "$VulkanPort",
    "-c", "16384", "-ngl", "99", "--jinja"
  )
  Start-Process -FilePath $Llama -ArgumentList $vArgs -WorkingDirectory (Split-Path $Llama -Parent) `
    -RedirectStandardOutput (Join-Path $Logs "vulkan.out.log") `
    -RedirectStandardError  (Join-Path $Logs "vulkan.err.log") `
    -WindowStyle Hidden
  Write-Host "Vulkan starting (1-3 min model load)..."

  if (Wait-Url "http://127.0.0.1:$VulkanPort/health" 90 2) {
    Write-Host "Vulkan healthy" -ForegroundColor Green
  } else {
    Write-Host "WARNING: Vulkan not healthy yet - check logs\vulkan.err.log" -ForegroundColor Yellow
  }

  Start-Process -FilePath $py -ArgumentList @(
    "-m", "realai.v3_orchestrator", "--host", "127.0.0.1", "--port", "$OrchPort"
  ) -WorkingDirectory $Root `
    -RedirectStandardOutput (Join-Path $Logs "v3-orchestrator.out.log") `
    -RedirectStandardError  (Join-Path $Logs "v3-orchestrator.err.log") `
    -WindowStyle Hidden

  if (Wait-Url "http://127.0.0.1:$OrchPort/health" 30 1) {
    try {
      $h = Invoke-RestMethod "http://127.0.0.1:$OrchPort/health"
      Write-Host ("Orchestrator: {0} vulkan.ok={1}" -f $h.status, $h.vulkan.ok) -ForegroundColor Green
    } catch {
      Write-Host "Orchestrator up" -ForegroundColor Green
    }
  } else {
    Write-Host "WARNING: orchestrator not answering - check logs\v3-orchestrator.err.log" -ForegroundColor Yellow
  }
}

# ---------------------------------------------------------------------------
# 2) CURATED PROMOTE (APPLY - this is the real work)
# ---------------------------------------------------------------------------
if (-not $SkipPromote) {
  Write-Step "CURATED PROMOTE --apply (allowlist only, not dump scanners)"
  $promoteArgs = @((Join-Path $Root "scripts\curated_promote.py"))
  if ($Force) { $promoteArgs += "--force" }
  & $py @promoteArgs
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Promote reported issues (see output above)" -ForegroundColor Yellow
  } else {
    Write-Host "Curated promote finished" -ForegroundColor Green
  }
}

# ---------------------------------------------------------------------------
# 3) OPTIONAL scan (off by default - this was making the mess)
# ---------------------------------------------------------------------------
if ($Scan) {
  Write-Step "Optional discover scan (you asked for -Scan)"
  & $py (Join-Path $Root "scripts\heal_cli.py") discover desktop
}

# ---------------------------------------------------------------------------
# 4) OPTIONAL deepen
# ---------------------------------------------------------------------------
if ($DeepenLoops -gt 0) {
  Write-Step "Deepen loops x $DeepenLoops"
  for ($i = 1; $i -le $DeepenLoops; $i++) {
    Write-Host "--- deepen $i ---" -ForegroundColor Yellow
    & $py (Join-Path $Root "scripts\heal_cli.py") deepen
  }
}

# ---------------------------------------------------------------------------
# 5) VERIFY
# ---------------------------------------------------------------------------
Write-Step "Verify imports + health"
& $py -c "from realai.memory.engine import MEMORY_ENGINE; print('MEMORY_ENGINE', type(MEMORY_ENGINE).__name__)"
& $py -c "from realai.aura_memory import AuraMemory; print('AuraMemory', AuraMemory)"
& $py -c "from realai import v3_orchestrator; print('v3_orchestrator OK')"
& $py -c "from realai import model_catalog; print('model_catalog OK')"
& $py -c "from realai import self_heal; print('self_heal OK', hasattr(self_heal,'run_curated_promote'))"

$base = "http://127.0.0.1:$OrchPort"
try {
  $h = Invoke-RestMethod "$base/health"
  Write-Host ("health: {0} vulkan: {1}" -f $h.status, $h.vulkan.ok)
  try {
    $models = Invoke-RestMethod "$base/v1/models"
    $ids = @($models.data | ForEach-Object { $_.id })
    Write-Host ("models: {0}" -f ($ids -join ", "))
  } catch {
    Write-Host "models: (could not list)"
  }
} catch {
  Write-Host "health: not up yet (start stack or check logs)"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " Done. Promote = apply allowlist (not more maps)."
Write-Host "   Repo:  $Root"
Write-Host "   API:   http://127.0.0.1:$OrchPort"
Write-Host "   Chat:  powershell -File scripts\run_local_chat.ps1"
Write-Host "   Log:   $Root\recovered\CURATED_PROMOTE_LOG.json"
Write-Host "   Report:$Root\scan_results\CURATED_PROMOTE.md"
Write-Host " Cold-archive dumps:"
Write-Host "   python scripts\cold_archive_recovered.py"
Write-Host "============================================================" -ForegroundColor Green
