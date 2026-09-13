# Parked: era API server with Vulkan forward (2026-09-13)

User pasted an older api_server with Vulkan llama-server forwarding.

## Do not drop-in replace live realai/api_server.py
- Paste was syntax-corrupted mid-do_POST
- Missing imports; duplicate routes; old / UI conflict

## Salvaged into live
- Vulkan forward for POST /v1/chat/completions when REALAI_VULKAN_BASE is healthy
- Helpers: _vulkan_base, _vulkan_healthy, _vulkan_chat, _looks_like_local_placeholder
