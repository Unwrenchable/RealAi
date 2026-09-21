# Park nested dumps out of the live package.
# Run from C:\RealAI-clean AFTER pulling live/realai-clean-20260911.
# Does not delete. Moves trees into _quarantine so import realai stays clean.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root "realai\orchestration\v3_orchestrator.py"))) {
    Write-Error "Run from the RealAI-clean product tree. Missing hive gold."
}

$Stamp = Get-Date -Format "yyyyMMdd"
$Dest = Join-Path $Root "_quarantine\twins_$Stamp"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

$Candidates = @(
    "realai\realai",
    "realai\realai_repo",
    "realai\realai_sdk",
    "realai\grok_export_realai",
    "realai\deep_nests",
    "realai\from_nests",
    "realai\plugins\plugins",
    "realai\plugins\C_realai_plugins",
    "layout.tsx",
    "globals.css"
)

foreach ($Rel in $Candidates) {
    $Src = Join-Path $Root $Rel
    if (-not (Test-Path $Src)) {
        Write-Host "skip missing $Rel"
        continue
    }
    $Name = ($Rel -replace "[\\/]", "__")
    $Target = Join-Path $Dest $Name
    Write-Host "park $Rel -> $Target"
    git -C $Root mv -k $Rel $Target
}

Write-Host "Parked under $Dest"
Write-Host "Smoke: python -m realai.v3_orchestrator --help"
Write-Host "Smoke: python -c ""from realai.hive import hive_status; print(hive_status().get('ok'))"""
