@echo off
REM Stop ONLY the llama-server.exe whose command line contains Qwen3-14B and --port 8080.
setlocal

powershell -NoProfile -Command "$p = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'llama-server.exe' -and $_.CommandLine -like '*Qwen3-14B*' -and $_.CommandLine -like '*--port 8080*' }); if ($p.Count -eq 0) { Write-Host 'No matching Qwen3-14B llama-server on port 8080 found.'; exit 1 }; foreach ($x in $p) { Write-Host ('Stopping PID ' + $x.ProcessId); Stop-Process -Id $x.ProcessId -Force }; exit 0"
if errorlevel 1 (
  echo Nothing stopped.
) else (
  echo Qwen3-14B stopped.
)
pause
endlocal
