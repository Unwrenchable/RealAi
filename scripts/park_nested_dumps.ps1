# Park nested dumps out of the live package.
# Run from C:\RealAI-clean AFTER pulling live/realai-clean-20260911.
# Does not delete. Moves trees into _quarantine so import realai stays clean.
# One copier: extend $Candidates. Do not add a second script.
# Does not write shims. Leave a dest-empty shim by hand only when rg finds a live importer.
# Never moves paths already under _quarantine\twins_20260921* or twins_20260924.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root "realai\orchestration\v3_orchestrator.py"))) {
    Write-Error "Run from the RealAI-clean product tree. Missing hive gold."
}

$Stamp = Get-Date -Format "yyyyMMdd"
$Dest = Join-Path $Root "_quarantine\twins_$Stamp"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

$Candidates = @(
    # Phase 1 — already on the shelf; skipped when the source is gone.
    "realai\realai",
    "realai\realai_repo",
    "realai\realai_sdk",
    "realai\grok_export_realai",
    "realai\deep_nests",
    "realai\from_nests",
    "realai\plugins\plugins",
    "realai\plugins\C_realai_plugins",
    "layout.tsx",
    "globals.css",
    # Phase 2 (2026-09-26) — remaining nested dumps. rg: no live importer.
    "realai\orchestrator-default-run",
    "realai\agent-tools-orchestrator-default-run",
    "realai\agents-orchestrator-default-run",
    "realai\ai-orchestrator-default-run",
    "realai\core_unify_20260830",
    "realai\orchestration_gold",
    "realai\realai-core",
    "realai\realai-frontend",
    "realai\exportable",
    "realai\v18",
    "realai\variants",
    # Phase 3 (2026-09-26) — one import path. rg: no live importer, so no shim.
    # Already moved when this list is extended; skipped when the source is gone.
    "realai\plugins\abilities",
    "realai\apps",
    "apps\frontend",
    "abilities\realai",
    "agents\realai",
    "apps\fusion-ui",
    "realai\fusion-ui",
    "realai\modules\desktop_unique",
    "realai\modules\self_improvement",
    "realai\modules\training"
    # Torch nn files (realai\modules\*.py except __init__.py) were moved as a
    # group to _quarantine\twins_20260926\realai__modules__torch_nn. Not listed
    # one-by-one so a later run cannot treat a missing file as a failure mode
    # beyond "skip missing".
)

foreach ($Rel in $Candidates) {
    if ($Rel -match '(?i)^_quarantine\\twins_20260921' -or $Rel -match '(?i)^_quarantine\\twins_20260924') {
        Write-Host "skip already shelved $Rel"
        continue
    }
    $Src = Join-Path $Root $Rel
    if (-not (Test-Path $Src)) {
        Write-Host "skip missing $Rel"
        continue
    }
    $Name = ($Rel -replace "[\\/]", "__")
    $Target = Join-Path $Dest $Name
    if (Test-Path $Target) {
        Write-Host "skip dest exists $Target"
        continue
    }
    Write-Host "park $Rel -> $Target"
    git -C $Root mv -k $Rel $Target
}

Write-Host "Parked under $Dest"
Write-Host "Smoke: python -m realai.v3_orchestrator --help"
Write-Host "Smoke: python -c ""from realai.hive import hive_status; print(hive_status().get('ok'))"""
