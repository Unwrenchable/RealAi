#Requires -Version 5.1
<#
.SYNOPSIS
  Install RealAI toolkit onto PATH so every useful command works from any project.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\RealAI-clean\scripts\install_global.ps1
#>
param(
    [string]$HomeDir = "C:\RealAI-clean",
    [switch]$NoPath
)

$ErrorActionPreference = "Stop"
$HomeDir = (Resolve-Path $HomeDir).Path
$BinDir = Join-Path $HomeDir "bin"

if (-not (Test-Path (Join-Path $HomeDir "realai\__main__.py"))) {
    throw "Not a RealAI install: $HomeDir"
}
if (-not (Test-Path (Join-Path $BinDir "realai.cmd"))) {
    throw "Missing $BinDir\realai.cmd"
}

[Environment]::SetEnvironmentVariable("REALAI_HOME", $HomeDir, "User")
$env:REALAI_HOME = $HomeDir
Write-Host "REALAI_HOME = $HomeDir" -ForegroundColor Green

$shims = @(
    "realai.cmd",
    "realai-chat.cmd",
    "realai-code.cmd",
    "realai-heal.cmd",
    "realai-selfheal.cmd",
    "realai-stack.cmd",
    "realai-server.cmd",
    "realai-orch.cmd",
    "realai-health.cmd",
    "realai-models.cmd",
    "realai-doctor.cmd",
    "realai-setup.cmd",
    "realai-improve.cmd",
    "realai-promote.cmd",
    "realai-gui.cmd",
    "realai-local.cmd",
    "realai-here.cmd",
    "realai-stop.cmd",
    "realai-tools.cmd",
    "realai-build.cmd",
    "realai-loop.cmd",
    "realai-train.cmd"
)

$missing = @()
foreach ($s in $shims) {
    if (-not (Test-Path (Join-Path $BinDir $s))) { $missing += $s }
}
if ($missing.Count) {
    Write-Host "WARNING missing shims: $($missing -join ', ')" -ForegroundColor Yellow
}
else {
    Write-Host "Shims OK ($($shims.Count) commands) in $BinDir" -ForegroundColor Green
}

if (-not $NoPath) {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $userPath) { $userPath = "" }
    $parts = $userPath -split ";" | Where-Object { $_ -and $_.Trim() }
    if ($parts -notcontains $BinDir) {
        $newPath = if ($userPath.TrimEnd(";")) { "$userPath;$BinDir" } else { $BinDir }
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        $env:Path = "$env:Path;$BinDir"
        Write-Host "Added to user PATH: $BinDir" -ForegroundColor Green
    }
    else {
        Write-Host "PATH already contains: $BinDir" -ForegroundColor Cyan
    }
}

Write-Host ""
Write-Host "Done. Open a NEW terminal, then from any project:" -ForegroundColor Green
Write-Host "  cd C:\YourProject"
Write-Host "  realai-tools            # list everything"
Write-Host "  realai                  # chat here"
Write-Host "  realai-code fix the bug"
Write-Host "  realai-heal"
Write-Host "  realai-stack            # GPU + API + UI (once)"
Write-Host "  realai-health"
Write-Host "  realai-models"
Write-Host ""
Write-Host "This session:" -ForegroundColor Yellow
Write-Host "  & '$BinDir\realai-tools.cmd'"
