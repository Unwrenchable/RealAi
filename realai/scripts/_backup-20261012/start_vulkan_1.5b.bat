@echo off
REM RealAI Vulkan backend (post-train / VRAM-safe default).
REM Binaries: C:\llama-vulkan\llama-server.exe (+ llama-cli.exe)
REM Weights:  C:\models\checkpoints_lora
REM Craft LoRA train kills this server for VRAM; resume with this bat or:
REM   python scripts\vulkan_runtime.py resume
setlocal
set GGUF=%REALAI_GGUF%
if "%GGUF%"=="" set GGUF=%REALAI_TRAIN_RESUME_GGUF%
if "%GGUF%"=="" set GGUF=C:\models\checkpoints_lora\qwen2.5-coder-1.5b-instruct-q5_k_m.gguf
set NGL=%REALAI_NGL%
if "%NGL%"=="" set NGL=40
set CTX=%REALAI_CTX%
if "%CTX%"=="" set CTX=4096
echo Starting C:\llama-vulkan\llama-server.exe
echo   Model : %GGUF%
echo   API   : http://127.0.0.1:8080/v1
echo   ngl=%NGL% ctx=%CTX%
start "RealAI-Vulkan" "C:\llama-vulkan\llama-server.exe" -m "%GGUF%" --host 127.0.0.1 --port 8080 -c %CTX% -ngl %NGL% --jinja
endlocal
