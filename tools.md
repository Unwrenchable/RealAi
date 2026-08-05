# RealAI Tools Manifest

This document consolidates tool definitions and runtime policy behavior from:

- `schema/tool.schema.json`
- `realai/tools.py`
- `realai/server/tools_runtime.py`

---

## Tool Manifest Schema Summary

Canonical schema file: `schema/tool.schema.json`

Required top-level fields:
- `name`
- `description`
- `input_schema`
- `output_schema`
- `safety`

Safety block includes:
- `risk_level`: `low|medium|high|critical`
- `requires_approval`: bool
- `dry_run_supported`: bool
- `rate_limit_per_minute`: int
- `allowed_profiles`: `safe|balanced|power`

---

## Runtime Tool Registry Surfaces

### A) `realai/tools.py` (Unified Tool-Calling Protocol)

Core classes:
- `ToolSchema`
- `ToolRegistry`
- `ToolCallValidator`
- `ToolCallOptimizer`
- `SecureToolExecutor`

Registered built-in tools:
1. `web_research`
2. `execute_code`
3. `generate_image`
4. `translate`
5. `transcribe_audio`

Execution controls:
- schema validation
- per-tool rate limiting
- optional confirmation
- timeout + retry
- audit log records

### B) `realai/server/tools_runtime.py` (Structured server runtime)

Core classes:
- `ToolManifest`
- `ToolRuntime`

Default registered tools:
1. `web_search`
2. `file_read`
3. `web3_solana_rpc`

Runtime controls:
- permission-based authorization
- basic audit events
- tool listing endpoint compatibility (`/v1/tools` in structured router)

---

## Concrete Tool Catalog (Current Known)

## 1) web_research
**Source:** `realai/tools.py`  
**Type:** web  
**Description:** Search web for information on a query.  
**Input Schema (simplified):**
- `query` (string, required)
- `max_results` (integer, optional)  
**Safety:** safe

Example:
```json
{"name":"web_research","arguments":{"query":"realai capabilities","max_results":5}}
```

---

## 2) execute_code
**Source:** `realai/tools.py`  
**Type:** code  
**Description:** Execute code snippet in sandboxed environment.  
**Input Schema (simplified):**
- `code` (string, required)
- `language` (string, optional)  
**Safety:** restricted

Example:
```json
{"name":"execute_code","arguments":{"code":"print('hello')","language":"python"}}
```

---

## 3) generate_image
**Source:** `realai/tools.py`  
**Type:** media  
**Description:** Generate image from prompt.  
**Input Schema:**
- `prompt` (string, required)
- `size` (string, optional)  
**Safety:** safe

Example:
```json
{"name":"generate_image","arguments":{"prompt":"futuristic city skyline","size":"1024x1024"}}
```

---

## 4) translate
**Source:** `realai/tools.py`  
**Type:** language  
**Description:** Translate text to target language.  
**Input Schema:**
- `text` (string, required)
- `target_language` (string, required)  
**Safety:** safe

Example:
```json
{"name":"translate","arguments":{"text":"Hello world","target_language":"es"}}
```

---

## 5) transcribe_audio
**Source:** `realai/tools.py`  
**Type:** audio  
**Description:** Transcribe audio from path/URL.  
**Input Schema:**
- `audio_path` (string, required)
- `language` (string, optional)  
**Safety:** safe

Example:
```json
{"name":"transcribe_audio","arguments":{"audio_path":"sample.wav","language":"en"}}
```

---

## 6) web_search
**Source:** `realai/server/tools_runtime.py`  
**Type:** web  
**Permissions:** `network`  
**Safety Class:** `networked`  
**Timeout:** 8000 ms

Example:
```json
{"tool":"web_search","params":{"query":"latest realai docs"}}
```

---

## 7) file_read
**Source:** `realai/server/tools_runtime.py`  
**Type:** file  
**Permissions:** `filesystem.read`  
**Safety Class:** `restricted`  
**Timeout:** 5000 ms

Example:
```json
{"tool":"file_read","params":{"path":"docs/CAPABILITIES.md"}}
```

---

## 8) web3_solana_rpc
**Source:** `realai/server/tools_runtime.py`  
**Type:** web3  
**Permissions:** `web3.solana`  
**Safety Class:** `privileged`  
**Timeout:** 10000 ms

Example:
```json
{"tool":"web3_solana_rpc","params":{"method":"getHealth","params":[]}}
```

---

## Notes on Unification

- `realai/tools.py` and `realai/server/tools_runtime.py` currently represent two overlapping tool systems.
- For unified runtime behavior, align naming/schema across both and expose a single canonical registry adapter.
- The `schema/tool.schema.json` should be used as a normalization target for future convergence.
