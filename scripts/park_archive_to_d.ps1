#Requires -Version 5.1
<#
SYNOPSIS
  Finish parking RealAI archive trees from C: to D: with junctions.

DESCRIPTION
  Moves (or finishes moving) these folders onto D:\RealAI-archive and leaves
  junctions at the original C:\RealAI-clean paths so imports keep working:

    _quarantine  ->  D:\RealAI-archive\_quarantine
    imports      ->  D:\RealAI-archive\imports
    recovered    ->  D:\RealAI-archive\recovered

  Safe to re-run. Uses robocopy to finish partial moves, then replaces the
  C: folder with a junction.

EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File C:\RealAI-clean\scripts\park_archive_to_d.ps1

NOTES
  Close apps that have files open under _quarantine / imports / recovered
  (IDE indexers, antivirus scans) if robocopy reports locked files.
#>

[CmdletBinding()]
param(
  [string]$RepoRoot = "C:\RealAI-clean",
  [string]$ArchiveRoot = "D:\RealAI-archive",
  [string[]]$Names = @("_quarantine", "imports", "recovered"),
  [switch]$WhatIf
)

$ErrorActionPreference = "Continue"

$logDir = Join-Path $RepoRoot "scan_results"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logPath = Join-Path $logDir ("park_archive_to_d_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))

function Write-Log([string]$Message) {
  $line = "{0:o}  {1}" -f (Get-Date), $Message
  Write-Host $line
  Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
}

function Test-IsJunction([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { return $false }
  $item = Get-Item -LiteralPath $Path -Force
  return [bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)
}

function Get-JunctionTarget([string]$Path) {
  $parent = Split-Path $Path -Parent
  $leaf   = Split-Path $Path -Leaf
  $out    = cmd /c "dir /AL `"$parent`"" 2>$null

  foreach ($line in $out) {
    if ($line -match [regex]::Escape($leaf) -and $line -match '

\[(.+)\]

\s*$') {
      return $Matches[1]
    }
  }
  return $null
}

function Ensure-ArchiveReadme {
  $readme = Join-Path $ArchiveRoot "README.md"
  $body = @"
# RealAI archive (parked off C:)

These trees are junctioned back into ``C:\RealAI-clean`` so paths keep working.

| Junction in repo | Real location |
|------------------|---------------|
| ``C:\RealAI-clean\_quarantine`` | ``D:\RealAI-archive\_quarantine`` |
| ``C:\RealAI-clean\imports``     | ``D:\RealAI-archive\imports``     |
| ``C:\RealAI-clean\recovered``   | ``D:\RealAI-archive\recovered``   |

Do not delete the D: folders while junctions remain.

Re-run: ``powershell -NoProfile -ExecutionPolicy Bypass -File C:\RealAI-clean\scripts\park_archive_to_d.ps1``
"@

  if (-not $WhatIf) {
    New-Item -ItemType Directory -Path $ArchiveRoot -Force | Out-Null
    Set-Content -LiteralPath $readme -Value $body -Encoding UTF8
  }
}

function Park-One([string]$Name) {
  $src  = Join-Path $RepoRoot $Name
  $dest = Join-Path $ArchiveRoot $Name

  Write-Log "==== $Name ===="
  Write-Log "src=$src"
  Write-Log "dest=$dest"

  # If C: missing but D: exists → create junction
  if (-not (Test-Path -LiteralPath $src) -and (Test-Path -LiteralPath $dest)) {
    Write-Log "C: path missing; creating junction -> D:"
    if ($WhatIf) { return }
    cmd /c "mklink /J `"$src`" `"$dest`"" | ForEach-Object { Write-Log $_ }
    return
  }

  if (-not (Test-Path -LiteralPath $src)) {
    Write-Log "SKIP: neither useful src present"
    return
  }

  # Already junction?
  if (Test-IsJunction $src) {
    $target = Get-JunctionTarget $src
    Write-Log "ALREADY junction (target=$target)"
    if ($target -and ($target -ieq $dest)) {
      Write-Log "OK pointing at archive"
      return
    }
    Write-Log "WARN: junction exists but target differs; leaving as-is"
    return
  }

  if ($WhatIf) {
    Write-Log "WhatIf: would robocopy /E /MOVE then junction"
    return
  }

  New-Item -ItemType Directory -Path $ArchiveRoot -Force | Out-Null
  New-Item -ItemType Directory -Path $dest -Force | Out-Null

  Write-Log "robocopy sync C -> D..."
  $robolog = Join-Path $logDir ("robocopy_{0}_{1:yyyyMMdd_HHmmss}.log" -f $Name, (Get-Date))

  $args = @(
    $src, $dest,
    "/E", "/COPY:DAT", "/DCOPY:DAT",
    "/XO", "/R:2", "/W:2",
    "/XD", "__pycache__", "node_modules", ".git",
    "/NFL", "/NDL", "/NP",
    "/LOG+:$robolog"
  )

  & robocopy @args | Out-Null
  $rc = $LASTEXITCODE
  Write-Log "robocopy exit=$rc (0-7 = OK) log=$robolog"

  if ($rc -ge 8) {
    Write-Log "ERROR: robocopy failed for $Name — fix locks and re-run"
    return
  }

  Write-Log "Removing C: copy..."
  try {
    Get-ChildItem -LiteralPath $src -Recurse -Force -EA SilentlyContinue |
      ForEach-Object { try { $_.Attributes = 'Normal' } catch {} }

    Remove-Item -LiteralPath $src -Recurse -Force -EA Stop
    Write-Log "Removed $src"
  } catch {
    Write-Log "WARN: could not fully delete ${src}: $($_.Exception.Message)"
    cmd /c "rd /s /q `"$src`"" | ForEach-Object { Write-Log $_ }
    if (Test-Path -LiteralPath $src) {
      Write-Log "ERROR: src still present — abort junction for $Name"
      return
    }
  }

  Write-Log "Creating junction $src <=> $dest"
  $linkOut = cmd /c "mklink /J `"$src`" `"$dest`"" 2>&1
  $linkOut | ForEach-Object { Write-Log $_ }

  if (Test-IsJunction $src) {
    Write-Log "SUCCESS $Name"
  } else {
    Write-Log "ERROR: junction missing after mklink for $Name"
  }
}

Write-Log "park_archive_to_d starting"
Write-Log "RepoRoot=$RepoRoot ArchiveRoot=$ArchiveRoot WhatIf=$WhatIf"

if (-not (Test-Path -LiteralPath "D:\")) {
  Write-Log "ERROR: D: drive not found"
  exit 1
}

Ensure-ArchiveReadme

foreach ($n in $Names) {
  Park-One $n
}

Write-Log "==== summary ===="
foreach ($n in $Names) {
  $src = Join-Path $RepoRoot $n
  $dest = Join-Path $ArchiveRoot $n
  $j = Test-IsJunction $src
  $dt = Test-Path -LiteralPath $dest
  Write-Log ("{0,-12} junction={1} dest={2}" -f $n, $j, $dt)
}

Write-Log "Done. Full log: $logPath"
Write-Host ""
Write-Host "Log: $logPath"
