$historyRoot = "C:\Users\tsmit\AppData\Roaming\Code\User\History"
$folders = @('723ed782','30ad1ddd','61e7bf2c','7db7a43b','65e6d2a6','-47a9047e','-77cc844d','3d3e65a5','688a22cd','-5b025901')

$cutoff = Get-Date "2026-07-04 00:00:00"   # ← July 4 midnight

$map = @{}

foreach ($f in $folders) {
    $dir = Join-Path $historyRoot $f
    if (-not (Test-Path $dir)) { continue }
    
    $entriesPath = Join-Path $dir "entries.json"
    if (-not (Test-Path $entriesPath)) { continue }
    
    $entries = Get-Content $entriesPath -Raw | ConvertFrom-Json
    
    Get-ChildItem $dir -File | Where-Object { $_.Name -ne "entries.json" } | ForEach-Object {
        if ($_.LastWriteTime -gt $cutoff) { return }   # skip Kilo era
        
        $origPath = $entries.resource -replace 'file:///c%3A/', 'C:\' -replace '%3A', ':' -replace '/', '\'
        $relPath = $origPath -replace '^C:\\Users\\tsmit\\realai\\', ''
        
        if (-not $map.ContainsKey($relPath) -or $_.LastWriteTime -gt $map[$relPath].Time) {
            $map[$relPath] = @{File=$_.FullName; Time=$_.LastWriteTime; Orig=$origPath}
        }
    }
}

Write-Host "Restoring files from before $cutoff ..." -ForegroundColor Green

foreach ($entry in $map.GetEnumerator()) {
    $dest = Join-Path (Get-Location) $entry.Key
    $parent = Split-Path $dest -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory $parent -Force | Out-Null }
    
    Copy-Item $entry.Value.File $dest -Force
    Write-Host "Restored: $($entry.Key)  [$( $entry.Value.Time )]" -ForegroundColor Cyan
}

Write-Host "Done! Run: git status" -ForegroundColor Green