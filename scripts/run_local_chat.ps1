<#
RealAI-clean local chat stack launcher
Compatible with Windows PowerShell 5.1 + PowerShell 7+

Starts Vulkan (:8080) + orchestrator (:8001) + optional UI (:3000),
then EXITS and LEAVES them running (detached - survive parent shell exit).

  powershell -File scripts\run_local_chat.ps1
  powershell -File scripts\run_local_chat.ps1 -SkipUI
  powershell -File scripts\run_local_chat.ps1 -Stop
#>

param(
    [switch]$SkipStart,
    [switch]$SkipUI,
    [switch]$SkipPromote,
    [switch]$Stop,
    [string]$Root        = "C:\RealAI-clean",
    [string]$Llama       = "C:\llama-vulkan\llama-server.exe",
    [string]$Model       = "",
    [int]$OrchPort       = 8001,
    [int]$VulkanPort     = 8080,
    [int]$UiPort         = 3000
)

# Operator system directive (Console Operator)
$__dirScript = Join-Path $Root 'scripts\set_operator_directive.ps1'
if (Test-Path $__dirScript) { . $__dirScript }

$ErrorActionPreference = "Continue"

# Canonical product root (never the realai\ package folder)
if ($Root -match '[\\/]realai[/\\]?$' -and (Test-Path (Join-Path (Split-Path $Root -Parent) 'scripts\run_local_chat.ps1'))) {
    $Root = Split-Path $Root -Parent
}
if (-not (Test-Path (Join-Path $Root 'scripts\run_local_chat.ps1')) -and (Test-Path 'C:\RealAI-clean\scripts\run_local_chat.ps1')) {
    $Root = 'C:\RealAI-clean'
}
if (-not $Model) {
    # Prefer env / checkpoints_lora (7B default; VRAM_SAFE=1 forces 1.5B)
    if ($env:REALAI_GGUF -and (Test-Path $env:REALAI_GGUF)) {
        $Model = $env:REALAI_GGUF
    } elseif ($env:REALAI_HIVE_GGUF -and (Test-Path $env:REALAI_HIVE_GGUF)) {
        $Model = $env:REALAI_HIVE_GGUF
    } elseif ($env:REALAI_TRAIN_RESUME_GGUF -and (Test-Path $env:REALAI_TRAIN_RESUME_GGUF)) {
        $Model = $env:REALAI_TRAIN_RESUME_GGUF
    } else {
        $vramSafe = if ($env:REALAI_VRAM_SAFE) { $env:REALAI_VRAM_SAFE } else { "0" }
        $ckpt = "C:\models\checkpoints_lora"
        $m15 = Join-Path $ckpt "qwen2.5-coder-1.5b-instruct-q5_k_m.gguf"
        $m7  = Join-Path $ckpt "qwen2.5-coder-7b-instruct-q5_k_m.gguf"
        if ($vramSafe -in @("1","true","yes") -and (Test-Path $m15)) {
            $Model = $m15
        } elseif (Test-Path $m7) {
            $Model = $m7
        } elseif (Test-Path $m15) {
            $Model = $m15
        } else {
            $Model = Join-Path $Root "models\qwen2.5-coder-7b-instruct-q5_k_m.gguf"
        }
    }
}

function Log {
    param([string]$msg, [string]$color = "White")
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $msg) -ForegroundColor $color
}

function Kill-Port {
    param([int[]]$Ports)
    foreach ($p in $Ports) {
        Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue |
            ForEach-Object {
                try { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
                catch {}
            }
    }
}

function Wait-Url {
    param([string]$Url, [int]$Tries = 60, [int]$SleepSec = 2)
    for ($i = 0; $i -lt $Tries; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { return $true }
        } catch {}
        if ($i -gt 0 -and ($i % 5) -eq 0) {
            Log ("  still waiting {0}... ({1}s)" -f $Url, ($i * $SleepSec)) "DarkGray"
        }
        Start-Sleep -Seconds $SleepSec
    }
    return $false
}

function Stop-Stack {
    Log "Stopping RealAI chat stack (ports $VulkanPort, $OrchPort, $UiPort)..." "Yellow"
    Kill-Port @($VulkanPort, $OrchPort, $UiPort)
    Get-Process -Name "llama-server" -ErrorAction SilentlyContinue |
        ForEach-Object { try { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue } catch {} }
    Log "Stack stopped." "Green"
}

# Start a process that outlives this script/job (cmd start + breakaway flags).
function Start-Detached {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory,
        [string]$StdoutLog,
        [string]$StderrLog,
        [string]$Title = "RealAI"
    )
    $argLine = ($ArgumentList | ForEach-Object {
        $a = "$_"
        if ($a -match '[\s"]') { '"' + ($a -replace '"', '\"') + '"' } else { $a }
    }) -join " "

    # Write a tiny one-shot cmd so quoting stays reliable
    $launcher = Join-Path $env:TEMP ("realai_launch_{0}_{1}.cmd" -f $Title, [Guid]::NewGuid().ToString("N").Substring(0, 8))
    $opFile = Join-Path $Root "docs\CONSOLE_OPERATOR_DIRECTIVE.md"
    $ggufLaunch = if ($env:REALAI_GGUF) { $env:REALAI_GGUF } elseif ($Model) { $Model } else { "" }
    $nctxLaunch = if ($env:REALAI_N_CTX) { $env:REALAI_N_CTX } elseif ($env:REALAI_CTX) { $env:REALAI_CTX } else { "65536" }
    $ttsLaunch = if ($env:REALAI_TTS_BACKEND) { $env:REALAI_TTS_BACKEND } else { "xtts" }
    $lines = @(
        "@echo off",
        "cd /d `"$WorkingDirectory`"",
        "set REALAI_HOME=$Root",
        "set REALAI_ROOT=$Root",
        "set REALAI_WORKSPACE=$Root",
        "set REALAI_PRODUCT_ROOT=$Root",
        "set REALAI_AGENTS_PATH=$Root\agents\agentx\agents.json",
        "set REALAI_AGENTS_SIM=1",
        "set PYTHONPATH=$Root;%PYTHONPATH%",
        "set REALAI_VULKAN_BASE=http://127.0.0.1:$VulkanPort",
        "set REALAI_API_BASE=http://127.0.0.1:$OrchPort",
        "set REALAI_DEFAULT_MODEL=realai-default-coder",
        "set REALAI_SELF_IMPROVE=true",
        "set REALAI_BOT_LOCAL_ONLY=1",
        "set REALAI_BOT_VOICE=1",
        "set REALAI_BOT_TOOLS=1",
        "set REALAI_TTS_BACKEND=$ttsLaunch",
        "set REALAI_MODELS_DIR=C:\models\checkpoints_lora",
        "set REALAI_API_KEY=local",
        "set PYTHONUNBUFFERED=1",
        "set REALAI_CTX=$nctxLaunch",
        "set REALAI_N_CTX=$nctxLaunch",
        "set REALAI_GGUF=$ggufLaunch",
        "set REALAI_OPERATOR_SYSTEM_FILE=$opFile",
        "`"$FilePath`" $argLine > `"$StdoutLog`" 2> `"$StderrLog`""
    )
    Set-Content -Path $launcher -Value ($lines -join "`r`n") -Encoding ASCII

    # /B background, new window group; process continues after parent exits
    $cmdArgs = "/c start `"$Title`" /MIN cmd /c `"$launcher`""
    Start-Process -FilePath "cmd.exe" -ArgumentList $cmdArgs -WindowStyle Hidden | Out-Null
    return $launcher
}

if ($Stop) {
    Stop-Stack
    exit 0
}

$Logs = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root "scan_results") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root "training\data") | Out-Null
Set-Location $Root

$env:REALAI_HOME          = $Root
$env:REALAI_ROOT          = $Root
$env:REALAI_VULKAN_BASE   = "http://127.0.0.1:$VulkanPort"
$env:REALAI_API_BASE      = "http://127.0.0.1:$OrchPort"
$env:NEXT_PUBLIC_API_URL  = "http://127.0.0.1:$OrchPort"
if (-not $env:REALAI_API_KEY) { $env:REALAI_API_KEY = "local" }
$env:REALAI_SELF_IMPROVE  = "true"
$env:ORCH_PORT            = "$OrchPort"
$env:REALAI_DEFAULT_MODEL = "realai-default-coder"
$env:REALAI_BACKEND_MODEL = [IO.Path]::GetFileName($Model)
$env:REALAI_GGUF          = $Model
$env:REALAI_MODELS_DIR    = "C:\models\checkpoints_lora"
$env:REALAI_VULKAN_DIR    = "C:\llama-vulkan"
$env:REALAI_TRAINING_DATA = Join-Path $Root "training\data"
$env:PYTHONPATH           = "$Root;$Root\realai"
$env:PYTHONUNBUFFERED     = "1"
if (-not $env:REALAI_BOT_LOCAL_ONLY) { $env:REALAI_BOT_LOCAL_ONLY = "1" }
if (-not $env:REALAI_BOT_VOICE) { $env:REALAI_BOT_VOICE = "1" }
if (-not $env:REALAI_BOT_TOOLS) { $env:REALAI_BOT_TOOLS = "1" }
if (-not $env:REALAI_TTS_BACKEND) { $env:REALAI_TTS_BACKEND = "kokoro" }
if (-not $env:REALAI_KOKORO_MODEL_DIR) { $env:REALAI_KOKORO_MODEL_DIR = "C:\models\checkpoints_lora\Kokoro" }
if (-not $env:REALAI_FISH_MODEL_DIR) { $env:REALAI_FISH_MODEL_DIR = "C:\models\checkpoints_lora\fish_speech_s1" }
if (-not $env:REALAI_XTTS_MODEL_DIR) { $env:REALAI_XTTS_MODEL_DIR = "C:\models\checkpoints_lora\xtts_v2" }

$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) { $Python = "python" }

if (-not $SkipStart) {
    try {
        Log "Cleaning ports $VulkanPort, $OrchPort..." "Cyan"
        Kill-Port @($VulkanPort, $OrchPort)
        Start-Sleep -Seconds 1

        if (-not (Test-Path $Llama)) { throw "Missing llama-server: $Llama" }
        if (-not (Test-Path $Model)) {
            $fallback = "C:\models\checkpoints_lora\qwen2.5-coder-1.5b-instruct-q5_k_m.gguf"
            $fallback7 = "C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf"
            if (Test-Path $fallback) {
                Log "GGUF not at $Model - using fallback $fallback" "Yellow"
                $Model = $fallback
            } elseif (Test-Path $fallback7) {
                Log "GGUF not at $Model - using fallback $fallback7" "Yellow"
                $Model = $fallback7
            } else {
                throw "Missing GGUF model: $Model (also missing checkpoints_lora fallbacks)"
            }
        }

        $ngl = if ($env:REALAI_NGL) { $env:REALAI_NGL } else { "99" }
        $ctx = if ($env:REALAI_CTX) {
            $env:REALAI_CTX
        } elseif ($env:REALAI_N_CTX) {
            $env:REALAI_N_CTX
        } else {
            "65536"
        }
        $env:REALAI_CTX = "$ctx"
        $env:REALAI_N_CTX = "$ctx"
        Log "Starting Vulkan server (C:\llama-vulkan + checkpoints_lora)..." "Cyan"
        Log "  model: $Model  ngl=$ngl ctx=$ctx" "DarkGray"
        $vLogOut = Join-Path $Logs "vulkan.out.log"
        $vLogErr = Join-Path $Logs "vulkan.err.log"
        Start-Detached -FilePath $Llama -ArgumentList @(
            "-m", $Model, "--host", "127.0.0.1", "--port", "$VulkanPort",
            "-c", "$ctx", "-ngl", "$ngl", "--jinja"
        ) -WorkingDirectory (Split-Path $Llama -Parent) `
          -StdoutLog $vLogOut -StderrLog $vLogErr -Title "RealAI-Vulkan"

        if (Wait-Url "http://127.0.0.1:$VulkanPort/health" 90 2) {
            Log "Vulkan healthy on :$VulkanPort" "Green"
        } else {
            throw "Vulkan not healthy - see logs\vulkan.err.log"
        }

        Log "Starting orchestrator on :$OrchPort..." "Cyan"
        $oLogOut = Join-Path $Logs "v3-orchestrator.out.log"
        $oLogErr = Join-Path $Logs "v3-orchestrator.err.log"
        Start-Detached -FilePath $Python -ArgumentList @(
            "-m", "realai.v3_orchestrator",
            "--host", "127.0.0.1",
            "--port", "$OrchPort"
        ) -WorkingDirectory $Root `
          -StdoutLog $oLogOut -StderrLog $oLogErr -Title "RealAI-Orch"

        if (Wait-Url "http://127.0.0.1:$OrchPort/health" 45 1) {
            try {
                $h = Invoke-RestMethod "http://127.0.0.1:$OrchPort/health"
                Log ("Orchestrator: {0} vulkan.ok={1}" -f $h.status, $h.vulkan.ok) "Green"
            } catch {
                Log "Orchestrator up" "Green"
            }
        } else {
            throw "Orchestrator not answering - see logs\v3-orchestrator.err.log"
        }
    }
    catch {
        Log "Startup failed: $_" "Red"
        Kill-Port @($VulkanPort, $OrchPort)
        exit 1
    }
}

if (-not $SkipPromote) {
    $Promote = Join-Path $Root "scripts\curated_promote.py"
    if (Test-Path $Promote) {
        Log "Applying curated promote allowlist..." "Cyan"
        try {
            & $Python $Promote
            if ($LASTEXITCODE -ne 0) { Log "Promote exit code $LASTEXITCODE (non-fatal)" "Yellow" }
        } catch { Log "Promote failed (non-fatal): $_" "Yellow" }
    }
}

Log "Chat smoke test..." "Cyan"
try {
    $Base = "http://127.0.0.1:$OrchPort"
    $Health = Invoke-RestMethod "$Base/health" -TimeoutSec 5
    Log ("Health: {0} Vulkan: {1}" -f $Health.status, $Health.vulkan.ok) "Green"

    $Body = @{
        model       = "realai-default-coder"
        messages    = @(@{ role = "user"; content = "Say hi in one short sentence." })
        max_tokens  = 64
        temperature = 0.2
    } | ConvertTo-Json -Depth 5

    $Resp = Invoke-RestMethod -Uri "$Base/v1/chat/completions" -Method POST -Body $Body -ContentType "application/json" -TimeoutSec 120
    Log ("Chat OK: {0}" -f $Resp.choices[0].message.content) "Green"
}
catch {
    Log "Verification failed: $_" "Yellow"
    Log "Check: logs\v3-orchestrator.err.log and logs\vulkan.err.log" "Yellow"
}

if (-not $SkipUI) {
    Log "Starting Next.js UI on port $UiPort..." "Cyan"
    $fe = Join-Path $Root "apps\frontend"
    if (-not (Test-Path (Join-Path $fe "package.json"))) {
        Log "No apps\frontend - skipping UI" "Yellow"
    }
    else {
        $envFile = Join-Path $fe ".env.local"
        @"
NEXT_PUBLIC_API_URL=http://127.0.0.1:$OrchPort
REALAI_API_BASE=http://127.0.0.1:$OrchPort
REALAI_API_KEY=local
"@ | Set-Content -Path $envFile -Encoding utf8

        if (-not (Test-Path (Join-Path $fe "node_modules"))) {
            Log "npm install (first run)..." "Yellow"
            Push-Location $fe
            npm install
            Pop-Location
        }

        Kill-Port @($UiPort)
        Start-Process -FilePath "cmd.exe" -ArgumentList @(
            "/c", "start", "RealAI-UI", "cmd", "/c",
            "cd /d `"$fe`" && npm run dev -- -p $UiPort"
        ) -WindowStyle Hidden | Out-Null
        Log "UI available at http://127.0.0.1:$UiPort" "Green"
    }
}

Log "============================================================" "Green"
Log " RealAI chat stack is RUNNING (background / detached)" "Green"
Log "   Chat UI:  http://127.0.0.1:$UiPort" "Green"
Log "   API:      http://127.0.0.1:$OrchPort/health" "Green"
Log "   Vulkan:   http://127.0.0.1:$VulkanPort/health" "Green"
Log "   Logs:     $Logs" "Green"
Log "   Terminal: realai" "Green"
Log "   Stop:     realai-stop" "Yellow"
Log "============================================================" "Green"
exit 0
