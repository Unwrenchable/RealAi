@echo off
REM Grok/Windows-friendly RealAI MCP launcher (stdio).
setlocal
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"
set "REALAI_HOME=C:\RealAI-clean"
set "REALAI_ROOT=C:\RealAI-clean"
set "PYTHONPATH=C:\RealAI-clean;%PYTHONPATH%"
if not defined REALAI_HIVE_URL set "REALAI_HIVE_URL=http://127.0.0.1:8001"
"C:\Program Files\Python312\python.exe" -u "C:\RealAI-clean\realai\mcp_server.py"
endlocal
