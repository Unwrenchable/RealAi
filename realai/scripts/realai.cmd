@echo off
REM Repo-root launcher — forces canonical HOME/WORKSPACE even from nested cwd.
set "PRODUCT_ROOT=%~dp0"
for %%I in ("%PRODUCT_ROOT%") do set "PRODUCT_ROOT=%%~fI"
set "REALAI_HOME=%PRODUCT_ROOT%\realai"
set "REALAI_ROOT=%REALAI_HOME%"
set "REALAI_PRODUCT_ROOT=%PRODUCT_ROOT%"
set "REALAI_WORKSPACE=%PRODUCT_ROOT%"
REM Product root ONLY — package is importable as realai via PRODUCT_ROOT.
set "PYTHONPATH=%PRODUCT_ROOT%;%PYTHONPATH%"
if not defined REALAI_API_KEY set REALAI_API_KEY=local
python -m realai %*
