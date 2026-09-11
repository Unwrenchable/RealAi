#!/bin/sh
# RealAI Voice Lab UI revive helper (port 8787 — Vulkan keeps 8080).
set -eu
cd "$(dirname "$0")"
if curl -sf -o /dev/null --max-time 2 http://127.0.0.1:8787/; then
  exit 0
fi
npm run dev >>/tmp/realai-voice-lab.log 2>&1 &
