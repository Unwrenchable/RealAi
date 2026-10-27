@echo off
setlocal
REM Rebuild the hive SFT dataset. Usage: build_dataset.bat [--dry-run] [--name NAME]
set "PY=C:\venvs\realai-train\Scripts\python.exe"
for /f "delims==" %%V in ('set REALAI_ 2^>nul') do set "%%V="
set "REALAI_HOME=C:\temp\realai-dsb-sources"
cd /d "%REALAI_HOME%"
echo [build_dataset] REALAI_HOME=%REALAI_HOME%
"%PY%" -m realai.training.dataset_builder --config config\dataset_builder.hive.pc.json %*
echo [build_dataset] exit %ERRORLEVEL%
pause
endlocal