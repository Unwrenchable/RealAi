@echo off
REM RealAI-clean — start stack + curated promote + verify
REM Phase 4: body lives in scripts\windows\. Product home is two levels up.
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set PYTHONPATH=%ROOT%\;%PYTHONPATH%
if not defined REALAI_API_KEY set REALAI_API_KEY=local

powershell -ExecutionPolicy Bypass -File "%ROOT%\scripts\run_local_selfheal.ps1" %*
if errorlevel 1 pause
