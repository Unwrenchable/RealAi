@echo off
REM ============================================================
REM RealAI — START HERE (canonical stack)
REM   Product home:  C:\RealAI-clean   (this folder)
REM   Python package: C:\RealAI-clean\realai\  (import realai.*)
REM
REM   Ports:
REM     Vulkan llama-server  :8080
REM     Hive orchestrator    :8001   (console / fusion / agents-ui)
REM     Voice Lab (optional) :8890
REM     Hive UI (optional)   :3000
REM ============================================================
setlocal
cd /d "%~dp0"

echo.
echo  RealAI canonical start
echo  ----------------------
echo  Product:  %CD%
echo  Package:  %CD%\realai
echo.
echo  [1] Full stack   Vulkan+Hive     -^> start_all.bat
echo  [2] Hive only    needs :8080     -^> start_orchestrator.bat
echo  [3] Vulkan only  GPU backend     -^> start_realai_server.bat
echo  [4] Voice Lab    TTS/STT :8890   -^> launches lab ^(detached^)
echo  [5] Hive UI      npm :3000       -^> start_ui.bat
echo  [0] Quit
echo.
choice /C 123450 /N /M "Pick [1-5,0]: "
set "C=%ERRORLEVEL%"
if "%C%"=="6" exit /b 0
if "%C%"=="1" goto STACK
if "%C%"=="2" goto ORCH
if "%C%"=="3" goto VULKAN
if "%C%"=="4" goto VOICE
if "%C%"=="5" goto UI
exit /b 0

:STACK
call "%~dp0start_all.bat" %*
exit /b %ERRORLEVEL%

:ORCH
call "%~dp0start_orchestrator.bat" %*
exit /b %ERRORLEVEL%

:VULKAN
call "%~dp0start_realai_server.bat" %*
exit /b %ERRORLEVEL%

:VOICE
call "%~dp0realai\voice\start_voice_lab.bat" %*
goto :eof
exit /b %ERRORLEVEL%

:UI
call "%~dp0start_ui.bat" %*
exit /b %ERRORLEVEL%
