@echo off
REM RealAI — approval orchestration worker (canonical -m entrypoint)
setlocal
cd /d "%~dp0"
set PYTHONPATH=%~dp0;%~dp0realai;%PYTHONPATH%
set REALAI_MODELS_DIR=C:\models\checkpoints_lora
set REALAI_LORA_ROOT=C:\models\checkpoints_lora
set PYTHONUNBUFFERED=1

echo Starting orchestration worker (modules.orchestrators.orchestration_worker)
echo Polls approvals, applies patches, notifies Slack/Teams when configured.
echo.

python -m modules.orchestrators.orchestration_worker
if errorlevel 1 pause
endlocal
