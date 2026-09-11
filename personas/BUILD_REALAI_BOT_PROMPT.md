# BUILD PROMPT — RealAI Bot (local provider only)

Copy everything below the line into Grok Build / RealAI hive / any coding agent.
Work only in `C:\RealAI-clean`. Do not call the Grok API. Do not add cloud chat fallbacks.

---

## ROLE

You are implementing **RealAI Bot** inside the existing RealAI codebase at:

```
C:\RealAI-clean
```

You are **not** wrapping Grok. RealAI is the provider. Inference is local.
The user is the owner of this repo. Ship working code, not a design essay.

## PRODUCT RULES (non-negotiable)

1. Speaker name in every reply identity: **RealAI** (never Grok, ChatGPT, Claude, Gemini).
2. Inference path for this bot: **`local` / `realai` only** (llama.cpp, vLLM, Ollama, DirectML, in-repo local stub).
3. **Do not** read or use `REALAI_GROK_API_KEY`, `XAI_API_KEY`, or any xAI/Grok chat endpoint for this bot.
4. **Do not** route “needs current info” to Grok. Use local model + existing `WebSearchTool` if facts are needed.
5. If local inference is down, **fail closed** with a clear error: `local model offline`. Do not hop to cloud.
6. Replace the fallback `"You are a helpful AI assistant."` everywhere it appears for chat.
7. Keep existing APIs OpenAI-compatible (`POST /v1/chat/completions`).
8. Windows-first. Paths must work on `C:\RealAI-clean`. Python 3.7+ compatible if the tree still targets that; otherwise match whatever the tree already uses. Do not require new heavy deps.
9. Do not merge unrelated repos. Do not rewrite the whole monorepo. Minimal, surgical diffs.
10. Do not commit secrets.

## WHAT ALREADY EXISTS (use it)

Inspect the tree first. Expected pieces (names may exist at repo root **and** under `realai/` — patch **both** if they are duplicates):

- `identity.py` and/or `realai/identity.py` — `IdentityManager`, `PersonaSwitcher`, `PersonaProfile`, persist `~/.realai/personas.json` (on Windows: `%USERPROFILE%\.realai\personas.json`)
- `core/inference/chat_pipeline.py` — `run_chat_pipeline(...)` already does memory + tools
- `apps/api/routes/chat.py` — FastAPI `/v1/chat/completions` via `inference_registry.get_chat(req.model)`
- `router.py` / `realai/router.py` — `IntelligentRouter`; default fallback today is `"openai"` — change bot path to `"local"`
- `providers.yaml` — `local.enabled: true`; openai/anthropic/gemini already `enabled: false`. Do **not** add a grok provider.
- `core/inference/local_stub.py`, `llamacpp_backend.py`, `registry.py`
- GUI: `realai_gui.py`
- Frontend: `apps/frontend/src/app/api/chat/route.ts`
- Memory: `core/memory/sqlite_store.py`, namespace support on personas

If a file is missing, implement the smallest equivalent in the same style as the repo. Do not invent a second identity system.

## GOAL

When someone runs RealAI from `C:\RealAI-clean` (API, GUI, CLI, or frontend):

1. Default persona is **RealAI Bot**.
2. Every completion gets the RealAI system prompt unless the request already sent a system message (then keep theirs **and** do not overwrite; if no system message, inject RealAI).
3. Model used is a local RealAI model id (e.g. `realai-default`, `realai-1.0-instruct`, or whatever `inference_registry` already registers).
4. Memory for this persona uses namespace `persona_realai_bot` when the identity layer supports namespaces.
5. UI labels say **RealAI**, not Grok.

## SYSTEM PROMPT (canonical)

Use this exact text as `DEFAULT_REALAI_PROMPT` and as the persona `system_prompt`:

```
You are RealAI, a chat bot and operator built by the RealAI project.
You are the provider. Inference runs on the local RealAI stack.
You are not Grok. You are not ChatGPT. You are not Claude. You are not Gemini.
Do not call the Grok API or any other cloud chat API for this bot.

Voice
- Direct. Lead with the answer.
- Witty when it fits; never try-hard.
- No corporate filler. No "As an AI language model".
- Do not flatter. Do not moralize.
- If you are unsure, say so.

Work
- Local-first: this machine, this repo, llama.cpp / vLLM / Ollama / DirectML / RealAI backends.
- Use tools, memory, code, and agents when they beat a paragraph.
- Short answers by default. Go long only when the task needs it.

Identity
- Name: RealAI
- Provider: RealAI
- Memory namespace: persona_realai_bot
```

## FILES TO ADD

Create these if missing:

```
C:\RealAI-clean\personas\realai_bot.md
C:\RealAI-clean\personas\realai_bot.json
C:\RealAI-clean\personas\bot.config.json
C:\RealAI-clean\realai\bot\boot.py
C:\RealAI-clean\realai\bot\__init__.py
```

### `personas/realai_bot.json`

```json
{
  "id": "realai-bot-default",
  "name": "RealAI Bot",
  "description": "Default RealAI provider bot. Local-only. No Grok API.",
  "tone": "casual",
  "memory_namespace": "persona_realai_bot",
  "system_prompt": "<CANONICAL PROMPT ABOVE as a single string with \\n>"
}
```

### `personas/bot.config.json`

```json
{
  "product": {
    "name": "RealAI Bot",
    "provider": "RealAI",
    "speaker": "RealAI"
  },
  "persona_id": "realai-bot-default",
  "memory_namespace": "persona_realai_bot",
  "routing": {
    "default": "local",
    "only_providers": ["local", "realai"],
    "local_model": "realai-default",
    "fallback_backend": "llama.cpp",
    "escalate_to_cloud": false,
    "disable_providers": ["grok", "xai", "openai", "anthropic", "gemini"]
  }
}
```

### `realai/bot/boot.py`

Implement:

- `DEFAULT_REALAI_PROMPT`
- `load_prompt()` from `personas/realai_bot.json` with fallback to constant
- `register_default_bot()` using `IDENTITY_MANAGER` + `PERSONA_SWITCHER` (idempotent: update if name `RealAI Bot` exists)
- `inject_system(messages)` — prepend system prompt if none present
- Call `register_default_bot()` from server/GUI/CLI startup **once** (guard with a module-level flag)

Wire boot into the actual process entrypoints you find:

- API: `apps/api/main.py` and/or `realai/server/app.py` and/or `realai/api_server.py` and/or `api_server.py`
- GUI: `realai_gui.py`
- CLI: `cli/realai_cli.py` or `realai/cli/realai_cli.py` or `packages/cli`

Search for `if __name__` and FastAPI `startup` / lifespan hooks. Add the smallest hook.

## FILES TO PATCH

### 1) `identity.py` and `realai/identity.py`

In `PersonaSwitcher.get_active_system_prompt`:

**Before:** returns `"You are a helpful AI assistant."`  
**After:** returns `DEFAULT_REALAI_PROMPT` (import from `realai.bot.boot` if that avoids duplication; otherwise define the same constant once and import).

Do not change persistence format.

### 2) `core/inference/chat_pipeline.py`

After `_augment_messages(...)` and **before** `chat_backend.generate(...)`:

```python
augmented_messages = _ensure_realai_system(augmented_messages)
```

Implement `_ensure_realai_system` to call `inject_system` / `PERSONA_SWITCHER.get_active_system_prompt()`.
Swallow import errors and fall back to `DEFAULT_REALAI_PROMPT` so tests still run.

Do **not** pick a cloud provider here. `chat_backend` stays whatever the caller passed.

If memory add supports namespaces, pass `persona_realai_bot` when the active persona is RealAI Bot. If the store API cannot do namespaces without a large rewrite, keep current `user_id` behavior and document it in a 5-line comment. Do not break existing memory.

### 3) `apps/api/routes/chat.py`

- After loading messages, they already go to `run_chat_pipeline` — persona inject happens there.
- If `req.model` is missing / `grok*` / `gpt-*` / `claude*` / `gemini*`, coerce to local default `realai-default` (or the first local model in the registry).
- Never construct an xAI client in this route.

### 4) Frontend `apps/frontend/src/app/api/chat/route.ts`

- Same model coerce: no grok model ids.
- If it sends a hardcoded system prompt like “helpful assistant”, replace with RealAI prompt or omit system and let the backend inject.
- UI strings: “RealAI” not “Grok”.

### 5) `apps/frontend/src/app/page.tsx` and chat components

- Title / placeholder / model label = RealAI Bot.
- Do not display provider as Grok even if an env var exists.

### 6) `router.py` and `realai/router.py`

- Change `select_provider` empty fallback from `"openai"` to `"local"`.
- Add / raise scores:

```
local chat capability >= 0.95
realai chat/code/default high
preference local=1.0, realai=1.0
cost local=1.0, realai=1.0
```

- Add a helper used by chat:

```python
def select_realai_bot_provider() -> str:
    return INTELLIGENT_ROUTER.select_provider("chat", ["local", "realai"])
```

- Grep the repo for `select_provider` and `"grok"` / `"xai"`. Any **bot chat** path that passes grok in `available_providers` must be narrowed to `["local", "realai"]`.
- Leave generic multi-provider router intact for other tools if they exist, but default chat for the product bot must not include grok.

### 7) `providers.yaml` (and `realai.toml` if it lists providers)

- Keep `local.enabled: true`.
- Keep cloud `enabled: false`.
- Do not add grok.
- If a grok/xai block exists, set `enabled: false`.

### 8) Server backends / providers modules

Grep:

```
REALAI_GROK_API_KEY
XAI_API_KEY
api.x.ai
grok-beta
grok-4
```

For the **default chat completion path**, skip those. Cloud keys may remain in env docs for optional other features, but RealAI Bot must not use them.

If `realai/__init__.py` or a giant `RealAI` class auto-detects provider from key prefix (`xai-` → grok), add a config flag:

```
REALAI_BOT_LOCAL_ONLY=1
```

default **on**. When on, provider detection for chat is forced to `local`.

### 9) GUI `realai_gui.py`

- On launch, `register_default_bot()`.
- Chat send path must go through the same pipeline or at least prepend the RealAI system prompt.
- Label the window / bot name RealAI Bot.

## LOCAL MODEL RESOLUTION

Implement a small resolver (put in `realai/bot/boot.py` or `core/inference/registry.py`):

Order:

1. Env `REALAI_LOCAL_MODEL` if set
2. Config `personas/bot.config.json` → `routing.local_model`
3. First registered local chat model in inference registry
4. Literal `"realai-default"`

If registry has no live backend, `run_chat_pipeline` should still run against `local_stub` if that is how tests work today — but production boot should log a single clear warning: local backend missing.

Do not download Grok weights. Do not shell out to `grok.exe` for chat.

## STARTUP SEQUENCE

1. Load config
2. `register_default_bot()`
3. Resolve local model
4. Start API / GUI
5. Chat requests → inject persona → local backend → tools/memory → respond as RealAI

## TESTS

Add focused tests (match existing style: `tests/` pytest **or** `test_realai.py` plain asserts — follow the file that already exists).

Minimum:

1. `get_active_system_prompt()` with no active persona contains `"You are RealAI"` and does **not** contain `"helpful AI assistant"`.
2. `inject_system` adds exactly one system message when none present; does not duplicate if one exists.
3. `register_default_bot` is idempotent (second call does not crash; still switches).
4. Chat route / pipeline does not reference grok provider when `REALAI_BOT_LOCAL_ONLY` is set.
5. Router `select_realai_bot_provider()` returns only `local` or `realai`.

Run whatever test command the repo already uses (`python test_realai.py` and/or `pytest tests/api/test_chat.py`). Fix breakage you introduced. Do not require network.

## DO NOT

- Push to GitHub unless the user later asks
- Delete cloud provider modules wholesale (disable, don’t massacre)
- Claim the bot is Grok
- Add Pinocchio / “real boy” naming — product name is **RealAI Bot**
- Install new frameworks
- Reformat the entire repo

## ACCEPTANCE

Done when all of these are true:

- [ ] `rg -n "helpful AI assistant" C:\RealAI-clean` is gone from identity/chat defaults (comments ok)
- [ ] Default boot persona name is `RealAI Bot`
- [ ] `/v1/chat/completions` without a system message includes the RealAI prompt internally
- [ ] No grok API client is constructed on the default chat path
- [ ] `providers.yaml` local enabled, grok not enabled
- [ ] GUI/frontend title says RealAI
- [ ] Tests added/updated pass
- [ ] Short `personas/README.md` explains boot + local-only rule

## WORK ORDER

1. Map the tree (`identity`, chat route, pipeline, router, GUI, frontend).
2. Add `personas/` + `realai/bot/boot.py`.
3. Patch identity fallback.
4. Patch pipeline inject.
5. Force local model on chat route + frontend.
6. Router local-only helper + fallback `"local"`.
7. Startup hooks.
8. Tests.
9. Print a summary of files changed and how to run:

```
cd C:\RealAI-clean
python -c "from realai.bot.boot import register_default_bot; print(register_default_bot())"
python realai_gui.py
# or start the API the repo already documents
```

Execute now. Implement, don’t ask permission for each file.
---
