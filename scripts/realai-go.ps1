# RealAI easy start — stack + open Console
$Root = "C:\RealAI-clean"
$env:REALAI_HOME = $Root
powershell -ExecutionPolicy Bypass -File "$Root\scripts\run_local_chat.ps1" -SkipUI -Root $Root
Start-Process "http://127.0.0.1:8001/console"
