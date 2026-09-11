@echo off
call "%~dp0_env.cmd" 2>nul
cd /d "%~dp0.."
call "%~dp0..\realai\voice\start_voice_lab.bat" %*
