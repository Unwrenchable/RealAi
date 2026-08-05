@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo  RealAI v3 — single authority stack  (C:\realai)
echo ============================================================
echo   Vulkan LLM     :8080   AMD GPU  (C:\llama-vulkan)
echo   Orchestrator   :8001   chat + agents + memory + self-heal
echo   Next UI        :3000   apps\frontend
echo ============================================================

set ROOT=%~dp0
set REALAI_VULKAN_BASE=http://127.0.0.1:8080
set REALAI_SELF_IMPROVE=true
set REALAI_TRAINING_DATA=%ROOT%training\data
set REALAI_DEFAULT_MODEL=qwen2.5-coder-7b-instruct-q5_k_m.gguf
set REALAI_MEMORY_INJECT=true
set REALAI_API_BASE=http://127.0.0.1:8001
set NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
set REALAI_API_KEY=local

REM --- 1) Vulkan ---
curl -s -m 2 http://127.0.0.1:8080/health >nul 2>&1
if errorlevel 1 (
  echo [1/3] Starting AMD Vulkan llama-server...
  start "RealAI-Vulkan" /MIN cmd /c "cd /d C:\llama-vulkan && llama-server.exe -m C:\realai\models\qwen2.5-coder-7b-instruct-q5_k_m.gguf --host 127.0.0.1 --port 8080 -c 8192 -ngl 99 --jinja"
  echo       Waiting for Vulkan health...
  set /a _n=0
  :wait_vk
  curl -s -m 2 http://127.0.0.1:8080/health >nul 2>&1
  if not errorlevel 1 goto vk_ok
  set /a _n+=1
  if !_n! GEQ 40 (
    echo ERROR: Vulkan did not become healthy in time.
    goto end
  )
  timeout /t 3 /nobreak >nul
  goto wait_vk
  :vk_ok
  echo       Vulkan OK
) else (
  echo [1/3] Vulkan already up on :8080
)

REM --- 2) Orchestrator ---
curl -s -m 2 http://127.0.0.1:8001/health >nul 2>&1
if errorlevel 1 (
  echo [2/3] Starting v3 orchestrator on :8001...
  start "RealAI-Orchestrator" /MIN cmd /c "cd /d %ROOT% && set REALAI_SELF_IMPROVE=true&& set REALAI_VULKAN_BASE=http://127.0.0.1:8080&& set REALAI_TRAINING_DATA=%ROOT%training\data&& set REALAI_MEMORY_INJECT=true&& python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001"
  timeout /t 4 /nobreak >nul
) else (
  echo [2/3] Orchestrator already up on :8001
)

REM --- 3) UI from C:\realai\apps\frontend only ---
set FE=%ROOT%apps\frontend
if not exist "%FE%\package.json" (
  echo ERROR: missing %FE%\package.json
  goto end
)
if not exist "%FE%\node_modules\next\package.json" (
  echo [3/3] Installing frontend deps once...
  pushd "%FE%"
  call npm install --no-fund --no-audit
  popd
)

REM write env for UI
(
echo REALAI_API_BASE=http://127.0.0.1:8001
echo REALAI_API_KEY=local
echo REALAI_PROVIDER=local
echo NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
) > "%FE%\.env.local"

curl -s -m 2 http://127.0.0.1:3000 >nul 2>&1
if errorlevel 1 (
  echo [3/3] Starting Next UI from %FE% ...
  start "RealAI-UI" /MIN cmd /c "cd /d %FE% && node_modules\.bin\next.cmd dev -p 3000 -H 127.0.0.1"
  timeout /t 10 /nobreak >nul
) else (
  echo [3/3] UI already up on :3000
)

echo.
echo ============================================================
echo  OPEN:  http://127.0.0.1:3000
echo  API:   http://127.0.0.1:8001/health
echo  GPU:   http://127.0.0.1:8080/health
echo  Heal:  http://127.0.0.1:8001/v1/self-heal/status
echo  Docs:  docs\AUTHORITY.md
echo ============================================================
echo.

:end
endlocal
