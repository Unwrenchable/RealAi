# RealAI ↔ Atomic Fizz Wiring Contract

**Document version:** 0.1.0  
**Date:** 2026-09-15  
**Audience:** Atomic Fizz / Caps engineers (integration) + RealAI maintainers  
**RealAI branch:** `live/realai-clean-20260911` (atomicfizz-coach **v0.1.0** — stub)  
**Related:** `REALAI_RACKUP_WIRING_CONTRACT.md` (same boundary pattern), [`ECOSYSTEM_BASE_URLS.md`](../ECOSYSTEM_BASE_URLS.md)  
**Purpose:** Production bridge so Atomic Fizz can run **player-level intelligence** on RealAI as its **Intelligence Provider** — same shape as RackUp / `rackup-coach`. **This revision is a stub:** abilities return structured placeholders. No Caps GPS, no Wrist UI chrome, no vault lookup, no runtime heal.

---

## 0. System boundary (non-negotiable)

| System | Owns | Does **not** own |
|--------|------|------------------|
| **RealAI** | Algorithms, validation **hints**, Wrist UI **hint copy**, Caps context **checks** (when implemented), health / contract discovery | Product UI, Caps device/runtime, Wrist chrome, vault GPS, world persistence, auth sessions, money movement |
| **Atomic Fizz** | App / Caps shell, Wrist UI, vault GPS, world state, match/session lifecycle, storing whatever RealAI returns | Inventing intelligence math inside the product; treating RealAI as an optional overlay |

**Relationship:** RealAI does **not** “live inside” Atomic Fizz as a bundled game system.  
RealAI is the **intelligence provider** that Caps / Wrist **call**.  
Atomic Fizz **calls** RealAI; Atomic Fizz **persists** results RealAI returns.

```
┌─────────────────────────────────────────────────────────┐
│  Atomic Fizz (product shell)                            │
│  - Caps, Wrist UI, vault GPS, world/session persistence │
│  - calls RealAI for intelligence / hints / validation   │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTPS JSON
                           ▼
┌─────────────────────────────────────────────────────────┐
│  RealAI (OpenAI-compatible provider + atomicfizz-coach) │
│  - stub abilities today; future Caps/Wrist hints        │
│  - NO Caps GPS, NO Wrist chrome, NO vault writes        │
│  - NO authorize_payout / NO money movement              │
└─────────────────────────────────────────────────────────┘
```

**Explicit:** Caps / Wrist UI / vault GPS stay **product-owned**. RealAI returns **hints and validation only**.

This plugin is **not** `atomic_fizz_realai` (recovered JS NPC/overseer engines under `realai/plugins/atomic_fizz_realai/`). That package is a separate gold archive and is not this contract.

---

## 1. Transport & endpoints

### 1.1 Base URL

```
REALAI_BASE_URL=<host>
```

Hosts and the Hive vs Render split: [`docs/ECOSYSTEM_BASE_URLS.md`](../ECOSYSTEM_BASE_URLS.md).

Default local API: `http://127.0.0.1:8000`  
Local Hive: `http://127.0.0.1:8001`

### 1.2 Primary intelligence entry (plugin-first)

| Method | Path | Use |
|--------|------|-----|
| `POST` | `/v1/plugins/atomicfizz-coach` | **Canonical** — all atomicfizz-coach abilities |
| `POST` | `/v1/atomicfizz/coach` | Optional alias of above |

**Plugin-first on Render.** Product hosts should call the canonical plugin path on the RealAI API (`REALAI_BASE_URL`), not invent a second protocol.

### 1.3 Local Hive dualism (documented, not required yet)

Local Hive (`http://127.0.0.1:8001`) already exposes `POST /v1/tools/execute` and a RackUp-specific `rackup_invoke` tool. Atomic Fizz **may** later grow a matching `atomicfizz_invoke` hive tool. **Do not wait on that.** Until it exists:

- Canonical integration is **plugin HTTP** on Render / `api_server`
- Hive `tools/execute` is optional local convenience, not the product contract
- There is **no** `atomicfizz_invoke` in this stub revision

### 1.4 Headers

```http
Content-Type: application/json
Authorization: Bearer <REALAI_API_KEY>   # optional; required only if the host enforces a service token
X-Request-Id: <uuid>                      # product correlation id (recommended)
X-Product-Tenant: <tenant-or-env>         # optional multi-env (generic form of X-RackUp-Tenant)
X-AtomicFizz-Tenant: <tenant-or-env>      # optional alias of X-Product-Tenant
X-Provider: realai                        # optional; local-first default
```

`X-Product-Tenant` is the **preferred generic tenant header** (same role as RackUp’s `X-RackUp-Tenant`). `X-AtomicFizz-Tenant` is an optional product-specific alias. RealAI does not require Atomic Fizz user JWTs. Atomic Fizz authenticates end users; RealAI trusts the **service** call (network policy / shared service token if exposed beyond localhost).

### 1.5 Python (same contract)

```python
from plugins.atomicfizz_coach import invoke

result = invoke("health", {"player_id": "p1"}, {})
result = invoke({
    "ability": "caps_context",
    "player": {"player_id": "p1"},
    "payload": {"tenant": "caps-dev"},
})
```

---

## 2. Universal request envelope

Every ability uses this shape against `POST /v1/plugins/atomicfizz-coach`:

```json
{
  "ability": "health",
  "player": {
    "player_id": "uuid-or-stable-id",
    "display_name": "optional"
  },
  "payload": {}
}
```

Python `invoke(ability, player, payload)` is the same fields, unpacked.

**Rule:** RealAI never queries Atomic Fizz’s DB or Caps GPS. If context matters, **the product must include it** in `player` / `payload`.

### 2.1 Universal response envelope

Aligned with `rackup-coach`:

```json
{
  "ok": true,
  "plugin": "atomicfizz-coach",
  "ability": "health",
  "result": {},
  "error": null
}
```

| Field | Type | Meaning |
|-------|------|---------|
| `ok` | bool | Ability succeeded |
| `plugin` | string | Always `atomicfizz-coach` |
| `ability` | string | Echo of requested ability |
| `result` | object | **Ability-specific payload for Atomic Fizz UI/state** |
| `error` | string\|null | Machine-readable failure |

**HTTP status:** `200` with `ok:false` may still be returned for unknown abilities / validation failures inside the body. Treat transport errors (5xx/network) separately from `ok:false`.

---

## 3. Ability contracts (stub)

All three abilities are **placeholders**. They must not crash. They must not pretend to implement Caps GPS, Wrist chrome, or vault I/O.

### 3.1 Health  
**`ability`: `health`** (alias: `ping`)

**When:** Liveness, contract discovery, deploy smoke.

**This is not a runtime heal.** No organs, no self-repair, no world mutation.

**Request:**

```json
{
  "ability": "health",
  "player": { "player_id": "p1" },
  "payload": {}
}
```

**Response `result` (shape):**

```json
{
  "status": "ok",
  "plugin": "atomicfizz-coach",
  "version": "0.1.0",
  "stub": true,
  "heal": false,
  "abilities": ["health", "caps_context", "wrist_ui_hint"],
  "player_id": "p1",
  "notes": "Placeholder health — contract discovery only; no runtime heal."
}
```

---

### 3.2 Caps context  
**`ability`: `caps_context`** (alias: `caps`)

**When:** Caps wants a validation / context hint before or during a session.

**Stub behavior:** Echo identity; return empty GPS/vault; state that Caps/GPS are product-owned.

**Request `payload` (optional):** `tenant`, plus any product-supplied facts (ignored for logic today).

**Response `result` (shape):**

```json
{
  "stub": true,
  "player_id": "p1",
  "tenant": "caps-dev",
  "caps": {
    "owned_by": "Atomic Fizz product",
    "gps": null,
    "vault": null,
    "hint": "Caps / vault GPS stay product-owned. RealAI returns validation hints only — no GPS implementation in this stub."
  },
  "validation": {
    "ok": true,
    "implemented": false,
    "warnings": [],
    "notes": "Placeholder Caps context — host must supply location/vault facts if they matter."
  },
  "persist_hint": {
    "owner": "Atomic Fizz product — RealAI does not persist Caps or GPS",
    "fields_to_write": []
  }
}
```

Atomic Fizz **must not** treat `gps: null` as “player has no location.” It means **RealAI did not compute GPS**.

---

### 3.3 Wrist UI hint  
**`ability`: `wrist_ui_hint`** (aliases: `wrist_ui`, `wrist`)

**When:** Wrist surface wants a hint payload to render.

**Stub behavior:** Return empty `actions` and placeholder copy. Product owns chrome.

**Response `result` (shape):**

```json
{
  "stub": true,
  "player_id": "p1",
  "owned_by": "Atomic Fizz Wrist UI",
  "hint": {
    "surface": "wrist",
    "copy": "Placeholder Wrist UI hint — product renders chrome.",
    "actions": [],
    "priority": "none"
  },
  "notes": "Wrist UI stays product-owned. RealAI returns hints only; no UI ownership."
}
```

---

## 4. What this stub will never do

| Action | Status |
|--------|--------|
| Runtime heal / self-repair | **Out of scope** (`health` is discovery only) |
| Caps GPS fix or vault geolocation | **Product-owned** |
| Wrist UI rendering / pip-boy chrome | **Product-owned** |
| `authorize_payout` / ledger posts / money movement | **Forbidden** — forever, not just this stub |
| Replacing `atomic_fizz_realai` JS engines | **Separate package** — do not conflate |

---

## 5. NestJS / product integration sketch

```ts
export async function realaiAtomicFizz(
  body: AtomicFizzCoachRequest,
): Promise<AtomicFizzCoachResponse> {
  const res = await fetch(
    `${process.env.REALAI_BASE_URL}/v1/plugins/atomicfizz-coach`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Request-Id': crypto.randomUUID(),
        ...(process.env.REALAI_API_KEY
          ? { Authorization: `Bearer ${process.env.REALAI_API_KEY}` }
          : {}),
        ...(process.env.ATOMICFIZZ_TENANT
          ? { 'X-Product-Tenant': process.env.ATOMICFIZZ_TENANT }
          : {}),
      },
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) throw new Error('RealAI unavailable');
  return res.json();
}
```

### Failure policy

| Failure | Product behavior |
|---------|------------------|
| RealAI timeout/5xx | Retry once; degrade to local product UX (never invent intelligence) |
| `ok: false` | Surface `error` / `result.available`; do not persist as success |
| Stub `implemented: false` | Treat as “not ready” — do not drive gameplay from placeholders |

---

## 6. Versioning & compatibility

| Item | Value |
|------|--------|
| Plugin | `atomicfizz-coach` **0.1.0** (stub) |
| Contract doc | **0.1.0** |
| Package folder | `realai/plugins/atomicfizz_coach` (Python import; one folder only) |
| HTTP slug | `atomicfizz-coach` |
| Breaking change policy | Bump plugin version; keep aliases (`ping`, `caps`, `wrist`) |

---

## 7. Security & privacy

- Send only **necessary** player fields (no passwords, no payment PANs, no wallet seeds).  
- Caps location, if ever sent, is product-supplied context — TLS only in production.  
- RealAI service should not be public without an auth gateway.  
- Optional Bearer `REALAI_API_KEY` when the host is exposed.

---

## 8. Quick reference — ability strings

| Ability string | Purpose | Stub? |
|----------------|---------|-------|
| `health` | Liveness / discovery | yes — not a heal |
| `caps_context` | Caps validation hints | yes — no GPS |
| `wrist_ui_hint` | Wrist hint payload | yes — no UI |

---

## 9. One-sentence contract

**Atomic Fizz is the product shell; RealAI is the intelligence provider — Caps, Wrist UI, and vault GPS stay in the product, RealAI returns hints and validation only via `POST /v1/plugins/atomicfizz-coach`, and RealAI never authorizes payouts or moves money.**
