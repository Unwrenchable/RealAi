@echo off
REM RealAI-clean — start stack + curated promote + verify
cd /d "%~dp0"
set PYTHONPATH=%~dp0;%PYTHONPATH%
if not defined REALAI_API_KEY set REALAI_API_KEY=local

powershell -ExecutionPolicy Bypass -File "%~dp0scripts\run_local_selfheal.ps1" %*
if errorlevel 1 pause
