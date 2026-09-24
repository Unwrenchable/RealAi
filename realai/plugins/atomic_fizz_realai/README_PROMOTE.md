# atomic_fizz_realai promote notes

- 
ealai-client.js — CJS hive client to http://127.0.0.1:8001 (LIVE wire-up).
- 
ealai-client.multiprovider.js — ESM multiprovider twin (OpenAI/Grok/Ollama); do not clobber hive client.
- ngines_src/ — promoted AFC scripts/realai/* ESM gold (size+symbols beat prior stubs).
- Generator stubs still use load-module.js, which resolves ngines_src then REALAI_AFC_VAULT/scripts/realai.
- Generators import AFC systems/region-influence — PARTIAL unless vault is present.
