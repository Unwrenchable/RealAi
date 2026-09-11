# RealAI Voice Lab — full Studio (Speak / Clone / Pipeline train)
# PowerShell (no cmd /d):
#   cd C:\RealAI-clean
#   .\realai\voice\start_voice_lab.ps1

param(
  [switch]$NoUi,
  [switch]$Simple,
  [switch]$Force
)

$ErrorActionPreference = 'Continue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $Root
$env:PYTHONPATH = "$Root;$Root\realai;$($env:PYTHONPATH)"
$env:REALAI_HOME = $Root
$env:REALAI_ROOT = $Root
$env:REALAI_PRODUCT_ROOT = $Root
$env:REALAI_BOT_VOICE = '1'
$env:REALAI_TTS_BACKEND = if ($env:REALAI_TTS_BACKEND) { $env:REALAI_TTS_BACKEND } else { 'xtts' }
$env:REALAI_XTTS_MODEL_DIR = if ($env:REALAI_XTTS_MODEL_DIR) { $env:REALAI_XTTS_MODEL_DIR } else { 'C:\models\checkpoints_lora\xtts_v2' }
$env:REALAI_XTTS_SPEAKER = if ($env:REALAI_XTTS_SPEAKER) { $env:REALAI_XTTS_SPEAKER } else { 'C:\models\checkpoints_lora\voices\unwrenchable.wav' }
$env:REALAI_KOKORO_MODEL_DIR = if ($env:REALAI_KOKORO_MODEL_DIR) { $env:REALAI_KOKORO_MODEL_DIR } else { 'C:\models\checkpoints_lora\Kokoro' }
$env:REALAI_KOKORO_VOICE = if ($env:REALAI_KOKORO_VOICE) { $env:REALAI_KOKORO_VOICE } else { 'af_heart' }

Write-Host ''
Write-Host '=== RealAI Voice Lab (full Studio) ==='
Write-Host '  API     http://127.0.0.1:8890'
Write-Host '  Studio  http://127.0.0.1:8787/   <- model pick / record / train'
Write-Host "  TTS     $($env:REALAI_TTS_BACKEND) · $($env:REALAI_XTTS_SPEAKER)"
Write-Host ''

$forcePy = if ($Force) { 'True' } else { 'False' }
$code = @"
from scripts.unified_stack import _base_env, start_voice_lab, start_voice_studio
import os, webbrowser, json
e = _base_env()
os.environ.update(e)
force = $forcePy
api = start_voice_lab(e, force=force)
print('api', api.get('status'), api.get('url'))
if not api.get('ok'):
    raise SystemExit(1)
"@

if ($NoUi) {
  $code += @"

print('skip ui')
"@
} elseif ($Simple) {
  $code += @"

webbrowser.open('http://127.0.0.1:8001/voice-lab/')
print('opened simple')
"@
} else {
  $code += @"

studio = start_voice_studio(e, force=force)
print('studio', studio.get('status'), studio.get('url'))
if studio.get('ok'):
    webbrowser.open(studio.get('url') or 'http://127.0.0.1:8787/')
else:
    print('studio_failed', studio)
    webbrowser.open('http://127.0.0.1:8001/voice-lab/')
    raise SystemExit(2)
"@
}

python -c $code
exit $LASTEXITCODE
