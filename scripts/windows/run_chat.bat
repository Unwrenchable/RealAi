@echo off
REM RealAI-clean — full local chat stack (Vulkan + orchestrator + UI)
REM Phase 4: body lives in scripts\windows\. Product home is two levels up.
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set PYTHONPATH=%ROOT%\;%PYTHONPATH%
if not defined REALAI_API_KEY set REALAI_API_KEY=local

where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
  pwsh -ExecutionPolicy Bypass -File "%ROOT%\scripts\run_local_chat.ps1" %*
) else (
  powershell -ExecutionPolicy Bypass -File "%ROOT%\scripts\run_local_chat.ps1" %*
)
