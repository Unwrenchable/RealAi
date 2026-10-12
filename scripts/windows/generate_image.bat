@echo off
REM RealAI local image generation (SDXL-Turbo, DirectML). No API keys.
REM Usage: generate_image.bat "a prompt"   (or double-click and type one)
setlocal
set REPO=C:\temp\realai-dsb-sources
set PY=C:\venvs\realai-train\Scripts\python.exe
set PROMPT=%~1
if "%PROMPT%"=="" set /p PROMPT=Prompt: 
if "%PROMPT%"=="" (echo No prompt. & pause & exit /b 1)
if not exist C:\models\image\out mkdir C:\models\image\out
cd /d %REPO%
set PYTHONPATH=%REPO%
"%PY%" -m realai.local_sdxl "%PROMPT%" --size 512x512 --steps 1
if errorlevel 1 (echo Generation failed. & pause & exit /b 1)
start "" C:\models\image\out
pause
