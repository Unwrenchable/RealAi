param(
    [Parameter(Mandatory=$true)]
    [string]$RootPath
)

# ============================================================
# RealAI Universal Clean Folder Listing Script
# Scans meaningful directories under ANY root path
# EXCLUDES: node_modules, .git, dist, build, cache, temp, etc.
# Saves clean list to <root>\recovered\REALAI_FOLDER_LIST.txt
# ============================================================

Write-Host "[scan] Starting clean folder listing for $RootPath ..." -ForegroundColor Cyan

# Output directory
$OutputDir = Join-Path $RootPath "recovered"
$OutputFile = Join-Path $OutputDir "REALAI_FOLDER_LIST.txt"

# Ensure output directory exists
if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
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
