@echo off
REM Stop whatever is listening on Voice Lab port (default 8890).
setlocal
if not defined REALAI_VOICE_LAB_PORT set "REALAI_VOICE_LAB_PORT=8890"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$port=%REALAI_VOICE_LAB_PORT%; $c=Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; if(-not $c){ Write-Host ('Port {0} already free' -f $port); exit 0 }; $procId=$c.OwningProcess; $proc=Get-CimInstance Win32_Process -Filter ('ProcessId={0}' -f $procId); Write-Host ('Stopping PID {0}: {1}' -f $procId, $proc.CommandLine); Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 1; Write-Host 'Stopped.'"
exit /b 0
