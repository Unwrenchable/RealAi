# daily_smoke.ps1 — quick local stack smoke from C:\RealAI-clean
#
# Working rackup-coach path (live hive :8001):
#   POST http://127.0.0.1:8001/v1/tools/execute
#   body: {"name":"rackup_invoke","arguments":{"ability":"roc_info"}}
# Discovery: GET/POST /v1/plugins/rackup-coach and /v1/rackup/coach returned 404 on
# live realai-v3-orchestrator. Scoped rg found those routes only in realai/api_server.py
# (not in live v3). Live path confirmed via GET /v1/tools (tool rackup_invoke) and
# POST /v1/tools/execute -> HTTP 200, result.plugin=rackup-coach.
# Also works: POST /v1/craft {"action":"rackup","ability":"roc_info"} and
# POST /v1/tools/execute {"name":"ability.coach","arguments":{}}.
# Note: curl -d $json breaks under powershell -File (invalid_json); use --data-binary @file.

Set-Location C:\RealAI-clean

Write-Host "=== health :8001 ==="
$h8001 = curl.exe -s http://127.0.0.1:8001/health
Write-Host $h8001

Write-Host "=== health :8080 ==="
$h8080 = curl.exe -s http://127.0.0.1:8080/health
Write-Host $h8080

$hiveOk = $h8001 -match '"status"\s*:\s*"ok"'
$vulkanOk = $h8080 -match '"status"\s*:\s*"ok"'

if (-not $hiveOk) {
    Write-Host "START_HIVE"
    exit 1
}
if (-not $vulkanOk) {
    Write-Host "START_VULKAN"
    exit 1
}

Write-Host "=== craft / architect_mode ==="
python -c "import realai.craft; from abilities.architect_mode import run_architect_mode; print('craft_ok', run_architect_mode)"

Write-Host "=== chat completions ==="
$chatFile = Join-Path $env:TEMP "daily_smoke_chat.json"
Set-Content -Path $chatFile -Value '{"model":"realai-hive","messages":[{"role":"user","content":"One sentence: how do I call rackup-coach from this hive?"}],"max_tokens":80}' -Encoding Ascii -NoNewline
curl.exe -s http://127.0.0.1:8001/v1/chat/completions -H "Content-Type: application/json" --data-binary "@$chatFile"
Write-Host ""

Write-Host "=== coach probe (POST /v1/tools/execute rackup_invoke) ==="
$coachFile = Join-Path $env:TEMP "daily_smoke_coach.json"
Set-Content -Path $coachFile -Value '{"name":"rackup_invoke","arguments":{"ability":"roc_info"}}' -Encoding Ascii -NoNewline
curl.exe -s -o NUL -w "coach_http=%{http_code}" -X POST http://127.0.0.1:8001/v1/tools/execute -H "Content-Type: application/json" --data-binary "@$coachFile"
Write-Host ""

Write-Host "=== console ==="
Start-Process http://127.0.0.1:8001/console
