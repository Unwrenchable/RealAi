@echo off
call "%~dp0_env.cmd" || exit /b 1
python -m realai stack --stop %*
