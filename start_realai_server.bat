@echo off
REM ============================================================
REM RealAI inference backend = llama-vulkan (AMD GPU), NOT Python UI
REM ============================================================
echo Starting RealAI backend via C:\llama-vulkan (AMD Vulkan)...
echo.
echo OpenAI-compatible API:
echo   http://127.0.0.1:8080/v1
echo.
echo Point RealAI / VS Code / clients at that base URL.
echo API Key: local
echo.
echo Optional models: qwen (default) | realai | 1b | llama
echo   start_realai_server.bat qwen
echo   start_realai_server.bat realai
echo.

set MODEL_ARG=%~1
if "%MODEL_ARG%"=="" set MODEL_ARG=qwen

call "C:\llama-vulkan\start_vulkan_server.bat" %MODEL_ARG%
