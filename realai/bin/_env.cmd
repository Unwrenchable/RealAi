@echo off
REM Shared env for all RealAI global shims (do not put on PATH alone).
REM
REM Canonical bind (this install):
REM   REALAI_HOME      = <product>\realai     (package)
REM   REALAI_WORKSPACE = <product>            (C:\RealAI-clean)
REM   PYTHONPATH       = <product> first      (so import realai works)

if defined REALAI_HOME (
  set "HOME_DIR=%REALAI_HOME%"
) else (
  REM bin\ is under product root → package is ..\realai
  set "HOME_DIR=%~dp0..\realai"
)
for %%I in ("%HOME_DIR%") do set "HOME_DIR=%%~fI"

REM If HOME was set to the product root, descend into realai\
if exist "%HOME_DIR%\realai\__main__.py" if not exist "%HOME_DIR%\__main__.py" (
  set "HOME_DIR=%HOME_DIR%\realai"
  for %%I in ("%HOME_DIR%") do set "HOME_DIR=%%~fI"
)

if not exist "%HOME_DIR%\__main__.py" (
  echo ERROR: RealAI package not found at "%HOME_DIR%"
  echo Expected: C:\RealAI-clean\realai\__main__.py
  echo Set REALAI_HOME or reinstall: powershell -File C:\RealAI-clean\scripts\install_global.ps1
  exit /b 1
)

for %%I in ("%HOME_DIR%\..") do set "PRODUCT_ROOT=%%~fI"

set "REALAI_HOME=%HOME_DIR%"
set "REALAI_ROOT=%HOME_DIR%"
set "REALAI_PRODUCT_ROOT=%PRODUCT_ROOT%"
REM ALWAYS force workspace to product root — never %CD% / nested folders
set "REALAI_WORKSPACE=%PRODUCT_ROOT%"
REM Product root ONLY — do not put package dir on PYTHONPATH (shadows stdlib logging).
set "PYTHONPATH=%PRODUCT_ROOT%;%PYTHONPATH%"

if not defined REALAI_API_KEY set "REALAI_API_KEY=local"
if not defined REALAI_DEFAULT_MODEL set "REALAI_DEFAULT_MODEL=realai-hive"
if not defined REALAI_BACKEND_MODEL set "REALAI_BACKEND_MODEL=qwen2.5-coder-7b-instruct-q5_k_m.gguf"
if not defined REALAI_HIVE_GGUF set "REALAI_HIVE_GGUF=C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf"
if not defined REALAI_MODELS_DIR set "REALAI_MODELS_DIR=C:\models\checkpoints_lora"
if not defined REALAI_N_CTX set "REALAI_N_CTX=16384"
if not defined REALAI_VULKAN_BASE set "REALAI_VULKAN_BASE=http://127.0.0.1:8080"
if not defined REALAI_API_BASE set "REALAI_API_BASE=http://127.0.0.1:8001"
if not defined REALAI_LLAMA_SERVER set "REALAI_LLAMA_SERVER=C:\llama-vulkan\llama-server.exe"
REM LoRA train backend: auto|directml|cuda|cpu  (Vulkan is inference-only / chat)
if not defined REALAI_TRAIN_DEVICE set "REALAI_TRAIN_DEVICE=directml"
if not defined TRAIN_OUTPUT_DIR set "TRAIN_OUTPUT_DIR=C:\models\checkpoints_lora"
if not defined TRAIN_DATASET_PATH set "TRAIN_DATASET_PATH=C:\models\checkpoints_lora\normalized_datasets\realai_lora_ready.jsonl"
if not defined REALAI_DIRECTML_DIR set "REALAI_DIRECTML_DIR=C:\DirectML\runtime\x64"
if exist "%REALAI_DIRECTML_DIR%\DirectML.dll" set "PATH=%REALAI_DIRECTML_DIR%;%PATH%"
exit /b 0
