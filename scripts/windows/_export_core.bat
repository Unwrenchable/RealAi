@echo off
setlocal
REM Shared core for export_spotcheck_1.5b / export_spotcheck_3b. Arg: <1.5b|3b>
REM Newest runs\sft-realai-hive-<size>* with adapter_best -> GGUF Q5_K_M -> serve :8081 -> spotcheck (tools + no tools) -> register (non-default).
set "PY=C:\venvs\realai-train\Scripts\python.exe"
set "WIN=C:\RealAI-clean\scripts\windows"
for /f "delims==" %%V in ('set REALAI_ 2^>nul') do set "%%V="
set "REALAI_HOME=C:\temp\realai-dsb-sources"
set "REALAI_LLAMA_CPP_ROOT=C:\tools\llama.cpp"
set "PYTHONPATH=C:\tools\llama.cpp\gguf-py"
cd /d "%REALAI_HOME%"
set "SIZE=%~1"
set "BASE=C:\models\hf\Qwen2.5-1.5B-Instruct"
if "%SIZE%"=="3b" set "BASE=C:\models\hf\Qwen2.5-3B-Instruct"
set "RUNDIR="
for /f "delims=" %%R in ('dir /b /ad /o-d "runs\sft-realai-hive-%SIZE%*" 2^>nul') do if not defined RUNDIR if exist "runs\%%R\adapter_best" if exist "runs\%%R\train_result.json" set "RUNDIR=%%R"
if not defined RUNDIR goto norun
set "MID=%RUNDIR:~4%"
set "OUT=runs\%RUNDIR%"
set "GGUF=%REALAI_HOME%\%OUT%\gguf\%MID%-Q5_K_M.gguf"
set "DS="
for /f "delims=" %%D in ('dir /b /ad /o-n "datasets\realai-hive-sft-*" 2^>nul') do if not defined DS set "DS=datasets\%%D"
echo ============================================================
echo  Export + spot-check: %SIZE%
echo  run      : %OUT%
echo  model id : %MID%
echo  gguf     : %GGUF%
echo ============================================================
echo Needs the GPU: stopping llama-server on 8080/8081 in 5 seconds.
echo Press Ctrl+C now to cancel.
timeout /t 5
call "%WIN%\stop_llama.bat" 8080 8081
echo.
echo [1/4] export (merge fp16 on CPU, convert, quantize Q5_K_M)...
"%PY%" -m realai.training.train_sft export --dataset %DS% --out %OUT% --base-model %BASE% --model-id %MID% --quant Q5_K_M
if errorlevel 1 goto failexport
if not exist "%GGUF%" goto failexport
echo.
echo [2/4] serving %MID% on :8081...
set "REALAI_8081_GGUF=%GGUF%"
call "%WIN%\start_realai_hive_8081.bat"
powershell -NoProfile -Command "$t=(Get-Date).AddSeconds(180); while((Get-Date) -lt $t){ try { if((Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://127.0.0.1:8081/health).StatusCode -eq 200){ exit 0 } } catch {}; Start-Sleep 3 }; exit 1"
if errorlevel 1 goto failserve
echo :8081 healthy.
echo.
echo [3/4] spot-check with tools, then without...
set "STAMP=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%"
set "RT=runs\spotcheck-%STAMP%-%MID%-tools.json"
set "RN=runs\spotcheck-%STAMP%-%MID%-notools.json"
"%PY%" -m realai.training.spotcheck --base-url http://127.0.0.1:8081 --model %MID% --label %MID%-tools --model-id %MID% --out %RT%
"%PY%" -m realai.training.spotcheck --base-url http://127.0.0.1:8081 --model %MID% --no-tools --label %MID%-notools --out %RN%
echo.
echo [4/4] register in ledger (non-default; --default is only allowed at 80%%+ via the gate)...
"%PY%" -m realai.training.train_sft register --dataset %DS% --out %OUT% --base-model %BASE% --model-id %MID% --quant Q5_K_M --spotcheck %RT%
echo.
powershell -NoProfile -Command "foreach($f in '%RT%','%RN%'){ if(Test-Path $f){ $j=Get-Content $f -Raw | ConvertFrom-Json; '{0}: {1}/{2} passed ({3:P0})' -f (Split-Path $f -Leaf),$j.passed,$j.n,[double]$j.pass_rate } }"
echo.
echo %MID% is still running on http://127.0.0.1:8081 for chess_match.bat. Stop it with stop_llama.bat 8081.
goto end
:norun
echo ERROR: no runs\sft-realai-hive-%SIZE%* with adapter_best and train_result.json. Train first.
goto end
:failexport
echo ERROR: export failed, no %GGUF%. See output above.
goto end
:failserve
echo ERROR: :8081 did not become healthy within 180 s. Check the "RealAI hive :8081" window.
:end
echo.
pause