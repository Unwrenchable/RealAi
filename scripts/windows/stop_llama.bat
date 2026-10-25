@echo off
setlocal
REM Stop llama-server listening on the given ports (default: 8080 8081).
REM   stop_llama.bat              stop 8080 and 8081
REM   stop_llama.bat 8081         stop only 8081
REM   stop_llama.bat --dry 8081   show what would be stopped, kill nothing
set "DRY=0"
if /i "%~1"=="--dry" (set "DRY=1" & shift)
set "PORTS="
:args
if "%~1"=="" goto done
set "PORTS=%PORTS% %~1"
shift
goto args
:done
if "%PORTS%"=="" set "PORTS=8080 8081"
for %%P in (%PORTS%) do (
  powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort %%P -State Listen -EA SilentlyContinue; if (-not $c) { 'port %%P: nothing listening' } else { $c | ForEach-Object { $p = Get-Process -Id $_.OwningProcess -EA SilentlyContinue; if ($p.ProcessName -ne 'llama-server') { 'port %%P: pid ' + $_.OwningProcess + ' is ' + $p.ProcessName + ' (not llama-server) - left alone' } elseif ('%DRY%' -eq '1') { 'port %%P: would stop llama-server pid ' + $_.OwningProcess } else { Stop-Process -Id $_.OwningProcess -Force; 'port %%P: stopped llama-server pid ' + $_.OwningProcess } } }"
)
endlocal