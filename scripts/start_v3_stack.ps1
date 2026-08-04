# RealAI v3 stack: Vulkan :8080 + Orchestrator :8001
$ErrorActionPreference = "Continue"
$Root = "C:\realai"
$Llama = "C:\llama-vulkan\llama-server.exe"
$Model = "C:\realai\models\qwen2.5-coder-7b-instruct-q5_k_m.gguf"
$Logs = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $Logs | Out-Null

# Free ports if held
foreach ($port in 8080, 8001) {
  Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
Start-Sleep -Seconds 1

# Vulkan llama-server
if (-not (Test-Path $Llama)) { throw "Missing $Llama" }
if (-not (Test-Path $Model)) { throw "Missing $Model" }
# Bind 0.0.0.0 so WSL and LAN tools can reach Vulkan (not only Windows localhost)
$vArgs = @(
  "-m", $Model,
  "--host", "0.0.0.0",
  "--port", "8080",
  "-c", "8192",
  "-ngl", "99",
  "--jinja"
)
Start-Process -FilePath $Llama -ArgumentList $vArgs -WorkingDirectory "C:\llama-vulkan" `
  -RedirectStandardOutput (Join-Path $Logs "vulkan.out.log") `
  -RedirectStandardError (Join-Path $Logs "vulkan.err.log") `
  -WindowStyle Hidden
Write-Host "Started llama-server (Vulkan) on :8080"

# Wait for health
for ($i=0; $i -lt 60; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) { Write-Host "Vulkan healthy"; break }
  } catch { Start-Sleep -Seconds 2 }
}

# Orchestrator
$env:REALAI_VULKAN_BASE = "http://127.0.0.1:8080"
$env:REALAI_SELF_IMPROVE = "true"
$env:ORCH_PORT = "8001"
$env:REALAI_DEFAULT_MODEL = "realai-default-coder"
$env:REALAI_BACKEND_MODEL = "qwen2.5-coder-7b-instruct-q5_k_m.gguf"
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "python" }
Start-Process -FilePath $py -ArgumentList @("-m","realai.v3_orchestrator","--host","127.0.0.1","--port","8001") `
  -WorkingDirectory $Root `
  -RedirectStandardOutput (Join-Path $Logs "v3-orchestrator.out.log") `
  -RedirectStandardError (Join-Path $Logs "v3-orchestrator.err.log") `
  -WindowStyle Hidden
Write-Host "Started v3 orchestrator on :8001"
Start-Sleep -Seconds 2
try {
  $h = Invoke-RestMethod "http://127.0.0.1:8001/health"
  Write-Host ("Orchestrator status: " + $h.status)
} catch { Write-Host "Orchestrator not answering yet" }
Write-Host "UI should use REALAI_API_BASE=http://127.0.0.1:8001"
