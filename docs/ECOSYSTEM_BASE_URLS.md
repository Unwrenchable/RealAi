# Ecosystem base URLs

Canonical hosts for RealAI and the product shells that call it as an **intelligence provider**. Products persist results; RealAI does not own product UI, GPS, or money movement.

## RealAI hosts

| Environment | Base URL | Role |
|-------------|----------|------|
| Local API (`api_server`) | `http://127.0.0.1:8000` | Plugin HTTP (`/v1/plugins/...`) |
| Local Hive (orchestrator) | `http://127.0.0.1:8001` | `POST /v1/tools/execute` + Hive tools |
| Render (example) | `https://realai-api.onrender.com` | Public intelligence host — **plugin-first** |

Set `REALAI_BASE_URL` to the host the product should call. Optional service token: `REALAI_API_KEY` (Bearer).

**Hive vs Render dualism:** local Hive may expose product tools (`rackup_invoke` today; a future `atomicfizz_invoke` later). Product integration should still treat **plugin HTTP on Render / `api_server`** as canonical. See the wiring contracts below.

## RackUp

Canonical: `POST {REALAI_BASE_URL}/v1/plugins/rackup-coach`  
Alias: `POST {REALAI_BASE_URL}/v1/rackup/coach`  
Contract: [`external_contracts/REALAI_RACKUP_WIRING_CONTRACT.md`](external_contracts/REALAI_RACKUP_WIRING_CONTRACT.md)

## Atomic Fizz / Caps

**Stub plugin `atomicfizz-coach` (v0.1.0) exists** so Caps can point at RealAI the same way RackUp points at `rackup-coach`. Canonical path: `POST {REALAI_BASE_URL}/v1/plugins/atomicfizz-coach` (optional alias `/v1/atomicfizz/coach`). Caps, Wrist UI, and vault GPS stay product-owned; RealAI returns hints/validation only and never authorizes payouts. Full envelopes: [`external_contracts/REALAI_ATOMICFIZZ_WIRING_CONTRACT.md`](external_contracts/REALAI_ATOMICFIZZ_WIRING_CONTRACT.md).
