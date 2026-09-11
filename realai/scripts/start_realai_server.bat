@echo off
echo Starting RealAI Local Server powered by llama.cpp server...
echo.
echo This will start a local OpenAI-compatible API server.
echo.
echo Configure RealAI with:
echo   API Base URL: http://127.0.0.1:8080/v1
echo   API Key: local (or any value)
echo.
echo Press Ctrl+C to stop the server
echo.

"C:\llama.cpp\build\bin\Release\llama-server.exe" ^
  -m "C:\Users\tsmit\OneDrive\Apps\realai\models\llama3.2-1b\Llama-3.2-1B-Instruct-Q4_K_M.gguf" ^
  --host 127.0.0.1 ^
  --port 8080 ^
  -c 4096 ^
  --log-disable

pause
