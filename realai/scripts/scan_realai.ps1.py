# ============================================
# SAFE RealAI Subsystem Recovery Scanner
# No server start/stop, no dispatch, no training.
# Pure filesystem scan + static reconstruction hints.
# ============================================

Write-Host "=== RealAI SAFE Subsystem Scanner ==="

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
    "C:\RealAI-clean\_quarantine\grok_export_realai\RealAI-clean",
    "C:\Users\tsmit\realai_historical_backups",
    "C:\Users\tsmit\backups",
    "D:\RealAI-archive",
    "D:\realai_archives"
)

# ---- Patterns to find ----
$patterns = @(
    "*benchmarks*bench*.py",
    "*bench_memory*.py",
    "*bench_tool_use*.py",
    "*bench_world*.py",
    "*bench_agent*.py",
    "*bench_stack*.py",
    "*bench_verify*.py",
    "*bench_promote*.py",
    "*bench_ability*.py",
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

# ---- Results container ----
$results = @()

# ---- Scan all roots ----
foreach ($root in $roots) {
    if (Test-Path $root) {
        Write-Host "`nScanning: $root"
        foreach ($pattern in $patterns) {
            $found = Get-ChildItem -Path $root -Recurse -ErrorAction SilentlyContinue -Filter $pattern
            foreach ($file in $found) {
                $results += [PSCustomObject]@{
                    Pattern = $pattern
                    File    = $file.FullName
                }
            }
        }
    } else {
        Write-Host "Missing root: $root"
    }
}

# ---- Output results ----
Write-Host "`n=== FOUND FILES ==="
$results | Format-Table -AutoSize

# ---- Save results ----
$outFile = "C:\RealAI-clean\scan_results\realai_recovery_scan.json"
$results | ConvertTo-Json -Depth 5 | Out-File $outFile -Encoding UTF8

Write-Host "`nSaved scan results to:"
Write-Host $outFile

Write-Host "`n=== SAFE SCAN COMPLETE ==="
