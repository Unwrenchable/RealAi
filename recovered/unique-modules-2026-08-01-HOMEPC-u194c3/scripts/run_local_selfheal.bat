@echo off
REM One-click RealAI local + self-heal + deepen
cd /d C:\realai
powershell -ExecutionPolicy Bypass -File "C:\realai\scripts\run_local_selfheal.ps1" %*
pause
