$drive = "D:\"

Write-Host "Scanning $drive for RealAI-related roots..." -ForegroundColor Cyan

# Folders we want to ignore completely
$ignore = @(
    "node_modules",
    ".pnpm",
    "dist",
    "build",
    "__pycache__",
    ".Trash-1000",
    "artifacts",
    "cache",
    "logs",
    "snapshots",
    "blobs"
)

# Patterns we DO want to find
$patterns = @(
    "realai",
    "realai-",
    "realai_",
    "realai ",
    "agent",
    "agents",
    "skills",
    "skill",
    "orchestration",
    "api",
    "cli",
    "sdk",
    "design-system",
    "tools_realai",
    "memory",
    "models",
    "hf_cache"
)

$results = @()

Get-ChildItem -Path $drive -Recurse -Directory -ErrorAction SilentlyContinue |
    Where-Object {
        # Ignore garbage folders
        $name = $_.Name.ToLower()
        -not ($ignore -contains $name)
    } |
    ForEach-Object {
        $folder = $_
        foreach ($pattern in $patterns) {
            if ($folder.Name -like "*$pattern*") {
                $results += [PSCustomObject]@{
                    Name = $folder.Name
                    FullPath = $folder.FullName
                }
                break
            }
        }
    }

$results | Sort-Object FullPath | Format-Table -AutoSize

# Export JSON for RealAI Architect Mode
$results | ConvertTo-Json -Depth 5 | Set-Content -Path "C:\RealAI-clean\scripts\realai_roots_D.json"

Write-Host "Scan complete. Results saved to realai_roots_D.json" -ForegroundColor Green
