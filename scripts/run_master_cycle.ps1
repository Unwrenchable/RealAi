# Quick launcher - run from C:\RealAI-clean
$ErrorActionPreference = "Continue"
$HomeDir = if ($env:REALAI_HOME) { $env:REALAI_HOME } else { "C:\RealAI-clean" }
Set-Location $HomeDir

Write-Host "=== RealAI Master Cycle ===" -ForegroundColor Magenta

# 1. Bootstrap (idempotent)
if (Test-Path ".\scripts\bootstrap_realai.ps1") {
    & .\scripts\bootstrap_realai.ps1
}

# 2. Full pipeline
if (Test-Path ".\scripts\auto_update_pipeline.py") {
    python .\scripts\auto_update_pipeline.py --rounds=3
} else {
    Write-Host "auto_update_pipeline.py missing - falling back to craft /dispatch all" -ForegroundColor Yellow
    $craft = ".\realai\cli\craft.py"
    if (Test-Path $craft) {
        python $craft "full automation"
    }
}

Write-Host "`nDone. Check logs\ under $HomeDir" -ForegroundColor Green
