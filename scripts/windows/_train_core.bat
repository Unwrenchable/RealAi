@echo off
setlocal
REM Shared core for train_1.5b / train_3b / resume_1.5b / resume_3b. Args: <1.5b|3b> <new|resume> [--test]
set "PY=C:\venvs\realai-train\Scripts\python.exe"
set "STOP=C:\RealAI-clean\scripts\windows\stop_llama.bat"
for /f "delims==" %%V in ('set REALAI_ 2^>nul') do set "%%V="
set "REALAI_HOME=C:\temp\realai-dsb-sources"
cd /d "%REALAI_HOME%"
set "SIZE=%~1"
set "MODE=%~2"
set "RUN=realai-hive-%SIZE%-next"
set "OUT=runs\sft-%RUN%"
set "BASE=C:\models\hf\Qwen2.5-1.5B-Instruct"
set "RECIPE="
if "%SIZE%"=="3b" set "BASE=C:\models\hf\Qwen2.5-3B-Instruct"
if "%SIZE%"=="3b" set "RECIPE=--dtype float16 --max-len 768 --lora-r 16 --grad-accum 32"
set "RES="
if "%MODE%"=="resume" set "RES=--resume auto"
if "%MODE%"=="resume" if not exist "%OUT%\checkpoint.json" goto nockpt
set "DS="
for /f "delims=" %%D in ('dir /b /ad /o-n "datasets\realai-hive-sft-*" 2^>nul') do if not defined DS set "DS=datasets\%%D"
if not defined DS goto nods
echo ============================================================
echo  RealAI LoRA training: %SIZE% (%MODE%)
echo  dataset : %DS%
echo  base    : %BASE%
echo  output  : %OUT%
echo ============================================================
echo Training needs the GPU: stopping llama-server on 8080/8081 in 5 seconds.
echo Press Ctrl+C now to cancel.
timeout /t 5
call "%STOP%" 8080 8081
echo.
echo "%PY%" -m realai.training.train_sft train --dataset %DS% --out %OUT% --base-model %BASE% --model-id %RUN% %RECIPE% %RES%
"%PY%" -m realai.training.train_sft train --dataset %DS% --out %OUT% --base-model %BASE% --model-id %RUN% %RECIPE% %RES%
echo.
echo [train] finished with exit code %ERRORLEVEL%
goto end
:nockpt
echo.
echo ERROR: nothing to resume. No checkpoint at %REALAI_HOME%\%OUT%\checkpoint.json
echo Start a fresh run with train_%SIZE%.bat first.
goto end
:nods
echo ERROR: no datasets\realai-hive-sft-* found in %REALAI_HOME%. Run build_dataset.bat first.
:end
echo.
pause