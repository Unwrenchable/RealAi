# Ecosystem Base URLs

**Document version:** 1.0.0  
**Date:** 2026-09-14  
**Status:** LOCKED — where clients point `REALAI_BASE_URL`  
**Audience:** RackUp Nest, Craft, local Hive, Render `api_server`, future product plugins  
**Related:** `REALAI_RACKUP_WIRING_CONTRACT.md` (ability envelopes — `ability` / `player` / `payload`)

Ability JSON does **not** change by host. Only the **base URL + path** change.

---

## 0. Two live hosts (intentional dualism)

| Host | Base URL | Coach LIVE path | Plugin route |
|------|----------|-----------------|--------------|
| **Local Hive / v3 orchestrator** | `http://127.0.0.1:8001` | `POST /v1/tools/execute` → `rackup_invoke` | `POST /v1/plugins/rackup-coach` often **404** |
| **Render `api_server`** (product RealAI API) | `https://<service>.onrender.com` | `POST /v1/plugins/rackup-coach` (alias `/v1/rackup/coach`) | **Required.** No Hive tools fallback |

This dualism is **intentional for now**. Document it forever. Hive plugin-route parity is **optional later** (backup-only), not a blocker.

---

## 1. Local Hive / v3 orchestrator

```
http://127.0.0.1:8001
```

Used by **Craft**, **Nest local**, and **Vulkan-forward chat**.

### RackUp coach LIVE path

```http
POST /v1/tools/execute
Content-Type: application/json
```

```json
{
  "name": "rackup_invoke",
  "arguments": { }
}
```

`arguments` is the same coach envelope as the plugin (`ability`, `player`, `payload`, …). See `REALAI_RACKUP_WIRING_CONTRACT.md`.

### Plugin route on Hive

```http
POST /v1/plugins/rackup-coach
```

Often **404 on Hive**. Do not treat that as a product outage. Prefer `rackup_invoke` via tools while talking to `:8001`.

---

## 2. Render `api_server` (product RealAI API)

```
https://<service>.onrender.com
```

Examples (illustrative, not pins): `https://realai-api.onrender.com`, `https://realai-qz3b.onrender.com`.

**Plugin-first. No Hive tools fallback.**

| Method | Path | Role |
|--------|------|------|
| `POST` | `/v1/plugins/rackup-coach` | Canonical coach |
| `POST` | `/v1/rackup/coach` | Alias of the above |

Do **not** call `POST /v1/tools/execute` + `rackup_invoke` against Render as a fallback.

---

## 3. Forbidden

`https://realaiui.vercel.app` is **UI only**.

**Never** set it as `REALAI_BASE_URL` (or `REALAI_API_BASE` / `NEXT_PUBLIC_API_URL`). Nest and Craft must talk to Hive or Render `api_server`, never the Vercel front door.

---

## 4. Env matrix

| Variable | Required | Notes |
|----------|----------|-------|
| `REALAI_BASE_URL` | **yes** | Hive `http://127.0.0.1:8001` **or** Render `https://…onrender.com`. Never the Vercel UI. |
| `REALAI_API_KEY` | optional | Sent as `Authorization: Bearer <key>` when the host requires a service token. |
| `REALAI_TENANT` | optional | Tenant / env id. |
| `RACKUP_TENANT` | optional | Alias of `REALAI_TENANT` on RackUp. |
| `X-RackUp-Tenant` | optional header | Same value on the wire (`X-RackUp-Tenant: <tenant-or-env>`). |
| `REALAI_COACH_PATH` | optional | Override path. Hive LIVE default conceptually `/v1/tools/execute`; Render default `/v1/plugins/rackup-coach`. |
| `REALAI_HIVE_TOOLS_FALLBACK` | optional `1`/`0` | **`1` only for Hive (`:8001`)** — use `rackup_invoke` when the plugin route 404s. **`0` on Render** — no tools fallback. |
| `REALAI_TIMEOUT_MS` | optional | Client timeout for coach calls. |

RackUp Render `REALAI_*` **pins** (which onrender host, keys, tenant) are owned by **roc**, not this file.

---

## 5. Ability envelopes

All coach abilities (`coach`, `shot_of_the_day`, `rating_update`, …) use the envelopes in:

**`docs/external_contracts/REALAI_RACKUP_WIRING_CONTRACT.md`**

This file does not redefine them. Host only selects base URL + path.

Jump / SOTD diagram stroke: `RACKUP_JUMP_PATH_SPEC.md` (straight airborne over blocker). Ghost: `RACKUP_GHOST_BALL_DIAGRAM_SPEC.md` (auto derive). Massé: `RACKUP_MASSE_CURVE_SPEC.md` (smooth curve).

---

## 6. Future product plugins

Atomic Fizz, Caps, and FizzSwap get their **own plugin stubs later**.

They reuse **this same base-URL matrix**:

- Local Hive `:8001` → tools / invoke path as that product ships it  
- Render `api_server` → `POST /v1/plugins/<product>` (plugin-first, no Hive fallback)  
- Never `realaiui.vercel.app` as `REALAI_BASE_URL`
