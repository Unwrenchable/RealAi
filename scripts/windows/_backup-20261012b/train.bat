@echo off
setlocal
REM LoRA SFT on the newest datasets\realai-hive-sft-*.
REM Usage: train.bat <1.5b|3b> <run_name> [--resume] [--dry-run] [--dataset DIR]
REM   3b  : C:\models\hf\Qwen2.5-3B-Instruct --dtype float16 --max-len 768 --lora-r 16 --grad-accum 32
REM   1.5b: C:\models\hf\Qwen2.5-1.5B-Instruct, recipe defaults (fp32, len 1024, r16, accum 16)
set "PY=C:\venvs\realai-train\Scripts\python.exe"
for /f "delims==" %%V in ('set REALAI_ 2^>nul') do set "%%V="
set "REALAI_HOME=C:\temp\realai-dsb-sources"
cd /d "%REALAI_HOME%"
if /i "%~1"=="--help" goto usage
if "%~2"=="" goto usage
set "SIZE=%~1"
set "RUN=%~2"
shift
shift
set "EXTRA="
set "DS="
:args
if "%~1"=="" goto parsed
if /i "%~1"=="--resume" (set "EXTRA=%EXTRA% --resume auto") else if /i "%~1"=="--dry-run" (set "EXTRA=%EXTRA% --dry-run") else if /i "%~1"=="--dataset" (set "DS=%~2" & shift) else (echo unknown option %~1 & goto usage)
shift
goto args
:parsed
if /i "%SIZE%"=="3b" (
  set "BASE=C:\models\hf\Qwen2.5-3B-Instruct"
  set "RECIPE=--dtype float16 --max-len 768 --lora-r 16 --grad-accum 32"
) else if /i "%SIZE%"=="1.5b" (
  set "BASE=C:\models\hf\Qwen2.5-1.5B-Instruct"
  set "RECIPE="
) else (
  echo size must be 1.5b or 3b
  goto usage
)
if not defined DS for /f "delims=" %%D in ('dir /b /ad /o-n "datasets\realai-hive-sft-*" 2^>nul') do if not defined DS set "DS=datasets\%%D"
if not defined DS (echo no datasets\realai-hive-sft-* found & exit /b 1)
for %%P in (8080 8081) do powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort %%P -State Listen -EA SilentlyContinue) { Write-Host 'WARNING: port %%P is in use (llama-server holds VRAM; training may OOM). Stop it with stop_llama.bat %%P' }"
set "CMD="%PY%" -m realai.training.train_sft train --dataset %DS% --out runs\sft-%RUN% --base-model %BASE% --model-id %RUN% %RECIPE%%EXTRA%"
echo %CMD%
%CMD%
echo [train] exit %ERRORLEVEL%
pause
exit /b 0
:usage
echo train.bat ^<1.5b^|3b^> ^<run_name^> [--resume] [--dry-run] [--dataset DIR]
exit /b 0