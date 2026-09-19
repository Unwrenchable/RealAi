# Load Console Operator directive into REALAI_OPERATOR_SYSTEM (UTF-8)
$Root = "C:\RealAI-clean"
if ($env:REALAI_HOME -and (Test-Path (Join-Path $env:REALAI_HOME "docs\CONSOLE_OPERATOR_DIRECTIVE.md"))) {
  $Root = $env:REALAI_HOME
}
$path = Join-Path $Root "docs\CONSOLE_OPERATOR_DIRECTIVE.md"
# Prefer repo-root docs even if REALAI_HOME is a nest
if (-not (Test-Path $path) -and (Test-Path "C:\RealAI-clean\docs\CONSOLE_OPERATOR_DIRECTIVE.md")) {
  $path = "C:\RealAI-clean\docs\CONSOLE_OPERATOR_DIRECTIVE.md"
}
if (Test-Path $path) {
  $env:REALAI_OPERATOR_SYSTEM = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
  Write-Host "[RealAI] REALAI_OPERATOR_SYSTEM loaded ($((Get-Item $path).Length) bytes) from $path"
} else {
  Write-Host "[RealAI] directive file missing: $path"
}