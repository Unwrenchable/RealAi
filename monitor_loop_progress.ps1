# RealAI Full-Loop Progress Monitor
# Run this in a second PowerShell window while the integrator is running

$base          = "C:\RealAI-clean"
$folderList    = Join-Path $base "recovered\REALAI_FOLDER_LIST.txt"
$promoteLog    = Join-Path $base "recovered\CURATED_PROMOTE_LOG.json"
$selfHealLog   = Join-Path $base "logs\last_self_heal.json"
$modelJson     = Join-Path $base "model.json"

# How many folders total
$total = (Get-Content $folderList -ErrorAction SilentlyContinue | Measure-Object).Count
if ($total -eq 0) { Write-Host "Folder list not found or empty." -ForegroundColor Red; exit }

# Track start time of this monitor session
$monitorStart = Get-Date
$lastPromoteTime = $null
$processedEstimate = 0

function Get-FileAgeSeconds($path) {
    if (Test-Path $path) {
        return [math]::Round(((Get-Date) - (Get-Item $path).LastWriteTime).TotalSeconds)
    }
    return $null
}

Write-Host "`n=== RealAI Loop Progress Monitor ===" -ForegroundColor Cyan
Write-Host "Total folders in list : $total"
Write-Host "Press Ctrl+C to stop`n"

while ($true) {
    $now = Get-Date

    # Latest activity timestamps
    $promoteAge = Get-FileAgeSeconds $promoteLog
    $healAge    = Get-FileAgeSeconds $selfHealLog

    # Detect if a new promote just happened
    $currentPromoteTime = if (Test-Path $promoteLog) { (Get-Item $promoteLog).LastWriteTime } else { $null }

    if ($currentPromoteTime -and $currentPromoteTime -ne $lastPromoteTime) {
        $processedEstimate++
        $lastPromoteTime = $currentPromoteTime
    }

    # Rough progress (we can only count promotions we observed)
    $pct = if ($total -gt 0) { [math]::Round(($processedEstimate / $total) * 100, 2) } else { 0 }

    # Time estimates
    $elapsed = ($now - $monitorStart).TotalMinutes
    $rate = if ($elapsed -gt 0 -and $processedEstimate -gt 0) { $processedEstimate / $elapsed } else { 0 }
    $remainingFolders = [math]::Max(0, $total - $processedEstimate)
    $etaMinutes = if ($rate -gt 0) { [math]::Round($remainingFolders / $rate, 1) } else { "calculating..." }

    # Status lines
    Clear-Host
    Write-Host "=== RealAI Loop Progress ===" -ForegroundColor Cyan
    Write-Host ("Time now          : {0}" -f $now.ToString("HH:mm:ss"))
    Write-Host ("Folders processed : {0} / {1}  ({2}%)" -f $processedEstimate, $total, $pct)
    Write-Host ("Processing rate   : {0:N2} folders/min" -f $rate)
    Write-Host ("ETA remaining     : {0} minutes" -f $etaMinutes)
    Write-Host ""
    Write-Host "Last promote age   : $(if ($promoteAge -ne $null) { "$promoteAge sec ago" } else { "none" })"
    Write-Host "Last self-heal age : $(if ($healAge -ne $null) { "$healAge sec ago" } else { "none" })"

    if (Test-Path $modelJson) {
        $ver = (Get-Content $modelJson | ConvertFrom-Json).version
        Write-Host "Model.json version : $ver"
    }

    Write-Host "`n(Refreshing every 10 seconds... Ctrl+C to exit)"
    Start-Sleep -Seconds 10
}