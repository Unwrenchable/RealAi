@echo off
REM RealAI — approval orchestration worker (canonical -m entrypoint)
setlocal
REM Phase 4: body lives in scripts\windows\. Product home is two levels up.
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set PYTHONPATH=%ROOT%\;%ROOT%\realai;%PYTHONPATH%
set REALAI_MODELS_DIR=C:\models\checkpoints_lora
set REALAI_LORA_ROOT=C:\models\checkpoints_lora
set PYTHONUNBUFFERED=1

echo Starting orchestration worker (modules.orchestrators.orchestration_worker)
echo Polls approvals, applies patches, notifies Slack/Teams when configured.
echo.

python -m modules.orchestrators.orchestration_worker
if errorlevel 1 pause
endlocal
