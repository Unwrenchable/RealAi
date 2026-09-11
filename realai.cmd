@echo off
REM Repo-root launcher — product home is THIS folder (not nested realai\).
set "PRODUCT_ROOT=%~dp0"
for %%I in ("%PRODUCT_ROOT%") do set "PRODUCT_ROOT=%%~fI"
REM Canonical: HOME = product root (matches start_all.bat / docs/REPO_LAYOUT.md)
set "REALAI_HOME=%PRODUCT_ROOT%"
set "REALAI_ROOT=%PRODUCT_ROOT%"
set "REALAI_PRODUCT_ROOT=%PRODUCT_ROOT%"
set "REALAI_WORKSPACE=%PRODUCT_ROOT%"
set "REALAI_PACKAGE=%PRODUCT_ROOT%\realai"
set "PYTHONPATH=%PRODUCT_ROOT%;%PYTHONPATH%"
if not defined REALAI_API_KEY set REALAI_API_KEY=local
if not defined REALAI_API_BASE set REALAI_API_BASE=http://127.0.0.1:8001
if not defined REALAI_VULKAN_BASE set REALAI_VULKAN_BASE=http://127.0.0.1:8080
python -m realai %*
