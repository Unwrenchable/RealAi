# Load Console Operator directive into REALAI_OPERATOR_SYSTEM (UTF-8).
# Natural Mode treats docs/CONSOLE_OPERATOR_DIRECTIVE.md as non-optional:
# realai/bot/boot.py loads it even when this script did not run.
$Root = "C:\RealAI-clean"
if ($env:REALAI_HOME -and (Test-Path (Join-Path $env:REALAI_HOME "docs\CONSOLE_OPERATOR_DIRECTIVE.md"))) {
  $Root = $env:REALAI_HOME
}
$scriptRepo = Split-Path -Parent $PSScriptRoot
$scriptDoc = Join-Path $scriptRepo "docs\CONSOLE_OPERATOR_DIRECTIVE.md"
$path = Join-Path $Root "docs\CONSOLE_OPERATOR_DIRECTIVE.md"
if (Test-Path $scriptDoc) {
  $path = $scriptDoc
}
if (-not (Test-Path $path) -and (Test-Path "C:\RealAI-clean\docs\CONSOLE_OPERATOR_DIRECTIVE.md")) {
  $path = "C:\RealAI-clean\docs\CONSOLE_OPERATOR_DIRECTIVE.md"
}
if (Test-Path $path) {
  $env:REALAI_OPERATOR_SYSTEM_FILE = $path
  $env:REALAI_OPERATOR_SYSTEM = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
  Write-Host "[RealAI] REALAI_OPERATOR_SYSTEM loaded ($((Get-Item $path).Length) bytes) from $path"
} else {
  Write-Host "[RealAI] directive file missing: $path"
}
