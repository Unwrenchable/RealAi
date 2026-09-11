#Requires -Version 5.1
<#
.SYNOPSIS
  Wire Microsoft DirectML (C:\DirectML) for AMD GPU PyTorch training on this machine.

  - Robocopies x64 DirectML.dll into Python torch_directml + RealAI vendor
  - Ensures PATH includes the runtime folder
  - Aligns torch==2.4.1 (required by torch-directml 0.2.5) and reinstalls torch-directml

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\RealAI-clean\scripts\setup_directml_amd.ps1
#>

param(
  [string]$DirectMlRoot = "C:\DirectML",
  [string]$RealAiRoot = "C:\RealAI-clean",
  [switch]$SkipPip
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$msg) {
  Write-Host ""
  Write-Host "==== $msg ====" -ForegroundColor Cyan
}

$src = Join-Path $DirectMlRoot "bin\x64-win"
if (-not (Test-Path (Join-Path $src "DirectML.dll"))) {
  throw "Missing DirectML.dll at $src (expected NuGet extract under C:\DirectML)"
}

$vendor = Join-Path $RealAiRoot "vendor\directml\x64"
New-Item -ItemType Directory -Force -Path $vendor | Out-Null

Write-Step "Robocopy DirectML runtime -> $vendor"
& robocopy $src $vendor "DirectML.dll" "DirectML.Debug.dll" /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
# robocopy exit 0-7 = success-ish
if ($LASTEXITCODE -ge 8) { throw "robocopy to vendor failed code=$LASTEXITCODE" }
Write-Host "OK: $(Join-Path $vendor 'DirectML.dll')"

# Discover python site-packages that already have torch_directml
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "python not on PATH" }
Write-Host "Python: $py"

$sites = & $py -c "import site; print('\n'.join(site.getsitepackages())); print(site.getusersitepackages())"
$siteList = @($sites -split "`r?`n" | Where-Object { $_ -and (Test-Path $_) })

$copiedTo = @()
foreach ($sp in $siteList) {
  $td = Join-Path $sp "torch_directml"
  if (Test-Path $td) {
    Write-Step "Robocopy DirectML.dll -> $td"
    & robocopy $src $td "DirectML.dll" /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy to $td failed code=$LASTEXITCODE" }
    # Also place next to the native pyd (loader often searches this dir)
    $pydDir = $sp
    & robocopy $src $pydDir "DirectML.dll" /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
    $copiedTo += $td
    Write-Host "OK: $td\DirectML.dll"
  }
}

# Machine-local runtime for PATH (safe, not System32)
$runtime = "C:\DirectML\runtime\x64"
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
Write-Step "Robocopy DirectML runtime -> $runtime (PATH)"
& robocopy $src $runtime "DirectML.dll" "DirectML.Debug.dll" /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy to runtime failed code=$LASTEXITCODE" }

# Persist user PATH entry
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $userPath) { $userPath = "" }
$parts = $userPath -split ";" | Where-Object { $_ -and $_.Trim() }
if ($parts -notcontains $runtime) {
  $newPath = if ($userPath.TrimEnd(";")) { "$userPath;$runtime" } else { $runtime }
  [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
  Write-Host "Added to user PATH: $runtime" -ForegroundColor Green
} else {
  Write-Host "PATH already has: $runtime" -ForegroundColor DarkGray
}
$env:Path = "$runtime;$env:Path"
[Environment]::SetEnvironmentVariable("REALAI_DIRECTML_DIR", $runtime, "User")
$env:REALAI_DIRECTML_DIR = $runtime

# RealAI env helper
$envCmd = Join-Path $RealAiRoot "bin\_env.cmd"
if (Test-Path $envCmd) {
  $txt = Get-Content $envCmd -Raw
  if ($txt -notmatch "REALAI_DIRECTML_DIR") {
    $insert = @"
if not defined REALAI_DIRECTML_DIR set "REALAI_DIRECTML_DIR=C:\DirectML\runtime\x64"
if exist "%REALAI_DIRECTML_DIR%\DirectML.dll" set "PATH=%REALAI_DIRECTML_DIR%;%PATH%"
"@
    # append before final exit
    $txt2 = $txt -replace "exit /b 0\s*$", ($insert + "`r`nexit /b 0`r`n")
    Set-Content -Path $envCmd -Value $txt2 -Encoding ASCII
    Write-Host "Updated bin\_env.cmd with REALAI_DIRECTML_DIR" -ForegroundColor Green
  }
}

if (-not $SkipPip) {
  Write-Step "Align PyTorch for torch-directml (requires torch==2.4.1)"
  Write-Host "Current torch may be incompatible (e.g. 2.11+cpu). Installing torch==2.4.1 + torch-directml..."
  & $py -m pip install --upgrade `
    "torch==2.4.1" `
    "torchvision==0.19.1" `
    "torch-directml==0.2.5.dev240914" `
    "transformers==4.44.2" `
    "peft==0.12.0" `
    "accelerate==0.33.0" `
    "tokenizers==0.19.1"
  if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

  # Re-copy DLL after reinstall (pip may overwrite package DirectML.dll)
  foreach ($sp in $siteList) {
    $td = Join-Path $sp "torch_directml"
    if (Test-Path $td) {
      & robocopy $src $td "DirectML.dll" /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
      & robocopy $src $sp "DirectML.dll" /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
    }
  }
  & robocopy $src $runtime "DirectML.dll" /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
}

Write-Step "Verify DirectML import + GPU device"
$probeFile = Join-Path $env:TEMP "realai_directml_probe.py"
@"
import os, sys
runtime = os.environ.get('REALAI_DIRECTML_DIR') or r'C:\DirectML\runtime\x64'
if runtime and os.path.isdir(runtime):
    os.environ['PATH'] = runtime + os.pathsep + os.environ.get('PATH', '')
print('python', sys.executable)
print('PATH_head', os.environ.get('PATH','').split(os.pathsep)[:3])
import torch
print('torch', torch.__version__)
import torch_directml
print('directml_count', torch_directml.device_count())
d = torch_directml.device()
print('device', d)
x = torch.randn(2, 2, device=d)
y = x @ x
print('matmul_ok', float(y.sum().cpu()))
print('SMOKE_PASS')
"@ | Set-Content -Path $probeFile -Encoding UTF8
$env:REALAI_DIRECTML_DIR = $runtime
$env:Path = "$runtime;$env:Path"
& $py $probeFile
if ($LASTEXITCODE -ne 0) {
  Write-Host "VERIFY FAILED - see errors above" -ForegroundColor Red
  exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " DirectML wired for AMD (RX 6700 XT class GPUs)."
Write-Host "   Runtime: $runtime"
Write-Host "   Vendor:  $vendor"
Write-Host "   Copied into torch_directml: $($copiedTo -join ', ')"
Write-Host " Open a NEW terminal, then:"
Write-Host "   python scripts\train_lora_local.py --device directml --max-steps 20"
Write-Host "============================================================" -ForegroundColor Green
