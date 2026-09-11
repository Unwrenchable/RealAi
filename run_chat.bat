@echo off
REM RealAI-clean — full local chat stack (Vulkan + orchestrator + UI)
cd /d "%~dp0"
set PYTHONPATH=%~dp0;%PYTHONPATH%
if not defined REALAI_API_KEY set REALAI_API_KEY=local

where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
  pwsh -ExecutionPolicy Bypass -File "%~dp0scripts\run_local_chat.ps1" %*
) else (
  powershell -ExecutionPolicy Bypass -File "%~dp0scripts\run_local_chat.ps1" %*
)
