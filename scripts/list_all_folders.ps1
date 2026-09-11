# ============================================================
# RealAI Clean Folder Listing Script
# Scans all meaningful directories under C:\RealAI-clean
# EXCLUDES: node_modules, .git, dist, build, cache, temp
# Saves clean list to recovered\REALAI_FOLDER_LIST.txt
# ============================================================

$RootPath = "D:\models","D:\realai_archives" 
$OutputFile = "$RootPath\recovered\REALAI_FOLDER_LIST.txt"

Write-Host "[scan] Starting clean folder listing..." -ForegroundColor Cyan

# Ensure output directory exists
if (!(Test-Path "$RootPath\recovered")) {
    New-Item -ItemType Directory -Path "$RootPath\recovered" | Out-Null
}

# Patterns to exclude
$ExcludePatterns = @(
    "node_modules",
    ".git",
    "dist",
    "build",
    "cache",
    "temp",
    "tmp",
    ".next",
    ".turbo",
    ".pnpm-store",
    ".vscode",
    ".idea"
)

# Recursively list all folders except excluded ones
Get-ChildItem -Path $RootPath -Directory -Recurse -Force |
    Where-Object {
        $full = $_.FullName.ToLower()
        foreach ($pattern in $ExcludePatterns) {
            if ($full -like "*$pattern*") { return $false }
        }
        return $true
    } |
    Select-Object -ExpandProperty FullName |
    Out-File -FilePath $OutputFile -Encoding UTF8

# Summary
$TotalFolders = (Get-Content $OutputFile).Count
Write-Host "[scan] Clean folder listing complete - $TotalFolders folders saved." -ForegroundColor Green
Write-Host "[scan] Output: $OutputFile" -ForegroundColor Yellow
Write-Host "[scan] Ready for RealAI integrator." -ForegroundColor Cyan
