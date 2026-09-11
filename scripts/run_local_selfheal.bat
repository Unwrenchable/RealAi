@echo off
cd /d "%~dp0.."
powershell -ExecutionPolicy Bypass -File "%~dp0run_local_selfheal.ps1" %*
if errorlevel 1 pause
