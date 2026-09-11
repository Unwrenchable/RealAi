# ============================================
# SAFE RealAI Reconstruction Script (Unified)
# ============================================

Write-Host "=== SAFE RealAI Reconstruction Script ==="

# ---- Directories to scan ----
$roots = @(
    "C:\RealAI-clean",
    "C:\RealAI-clean\realai",
    "C:\RealAI-clean\scripts",
    "C:\RealAI-clean\providers",
    "C:\RealAI-clean\packages",
    "C:\RealAI-clean\agents",
    "C:\RealAI-clean\memory",
    "C:\RealAI-clean\models",
    "C:\RealAI-clean\training",
    "C:\RealAI-clean\archive",
    "C:\RealAI-clean\.kilo",
    "C:\RealAI-clean\_quarantine",
    "C:\Users\tsmit\realai_historical_backups",
    "C:\Users\tsmit\backups",
    "D:\RealAI-archive",
    "D:\realai_archives"
)

# ---- Quarantine prefixes to strip ----
$prefixes = @(
    "C__realai_",
    "backup_clean_",
    "realai_og_mess_",
    "realai_.kilo_worktrees_"
)

# ---- Benchmark patterns ----
$benchPatterns = @(
    "*bench*.py",
    "*bench_memory*.py",
    "*bench_tool_use*.py",
    "*bench_world*.py",
    "*bench_agent*.py",
    "*bench_stack*.py",
    "*bench_verify*.py",
    "*bench_promote*.py",
    "*bench_ability*.py"
)

# ---- Gold-assembly patterns ----
$goldPatterns = @(
    "*assemble_gold*.py",
    "*promote_gold*.py",
    "*gold_index*.py",
    "*era_map*.py",
    "*dds3*.py",
    "*scan_messy_repo*.py",
    "*training_data*.py",
    "*promote_queue*.py",
    "*deep_gold*.py",
    "*archive_triage*.py",
    "*ability_inventory*.py",
    "*roots_ingest*.py",
    "*verify_matrix*.py",
    "*stack_health*.py"
)

# ---- Output containers ----
$foundFiles = @()
$renamedFiles = @()

# ---- Step 1: Strip quarantine prefixes ----
foreach ($root in $roots) {
    if (Test-Path $root) {
        Get-ChildItem -Path $root -Recurse -File | ForEach-Object {
            $old = $_.FullName
            $name = $_.Name
            foreach ($p in $prefixes) {
                if ($name.StartsWith($p)) {
                    $newName = $name.Replace($p, "")
                    $newPath = Join-Path $_.DirectoryName $newName
                    Rename-Item -LiteralPath $old -NewName $newName -Force
                    $renamedFiles += $newPath
                }
            }
        }
    }
}

# ---- Step 2: Copy benchmark modules ----
$benchDest = "C:\RealAI-clean\realai\benchmarks"
New-Item -ItemType Directory -Force -Path $benchDest | Out-Null

foreach ($root in $roots) {
    foreach ($pattern in $benchPatterns) {
        Get-ChildItem -Path $root -Recurse -File -Filter $pattern |
            Copy-Item -Destination $benchDest -Force
    }
}

# ---- Step 3: Generate __init__.py ----
$modules = Get-ChildItem -Path $benchDest -File -Filter "*.py"
$initPath = Join-Path $benchDest "__init__.py"
$content = ""

foreach ($m in $modules) {
    $name = [System.IO.Path]::GetFileNameWithoutExtension($m.Name)
    $content += "from .${name} import *`n"
}

Set-Content -Path $initPath -Value $content -Encoding UTF8

# ---- Step 4: Diff missing modules ----
$expected = @(
    "base.py",
    "bench_memory.py",
    "bench_tool_use.py",
    "bench_world_model.py",
    "bench_agent_eval.py",
    "bench_stack_health.py",
    "verify_v3_matrix.py",
    "promote_eval.py",
    "ability_matrix.py"
)

$existing = Get-ChildItem -Path $benchDest -File | Select-Object -ExpandProperty Name
$missing = $expected | Where-Object { $_ -notin $existing }

# ---- Step 5: Restore gold-assembly components ----
$goldDest = "C:\RealAI-clean\scripts"
New-Item -ItemType Directory -Force -Path $goldDest | Out-Null

foreach ($root in $roots) {
    foreach ($pattern in $goldPatterns) {
        Get-ChildItem -Path $root -Recurse -File -Filter $pattern |
            Copy-Item -Destination $goldDest -Force
    }
}

# ---- Save results ----
$outFile = "C:\RealAI-clean\scan_results\realai_reconstruction.json"
$report = [PSCustomObject]@{
    Renamed = $renamedFiles
    MissingBenchmarks = $missing
    BenchmarksCopied = (Get-ChildItem $benchDest -File).FullName
    GoldAssemblyCopied = (Get-ChildItem $goldDest -File).FullName
}

$report | ConvertTo-Json -Depth 5 | Out-File $outFile -Encoding UTF8

Write-Host "`n=== SAFE Reconstruction Complete ==="
Write-Host "Report saved to: $outFile"
