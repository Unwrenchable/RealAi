# Implement a RealAI-only chat persona called RealAI Bot inside C:\\RealAI-clean.

# 

# Rules:

# \- No Grok, no xAI, no OpenAI, no Anthropic, no Gemini.

# \- No cloud routing, no cloud fallbacks, no cloud clients.

# \- Do not clone the repo, do not copy directories, do not duplicate realai/.

# \- Modify existing files only inside C:\\RealAI-clean.

# 

# Tasks:

# 1\. Create these files if missing:

# &#x20;  - personas/realai\_bot.md

# &#x20;  - personas/realai\_bot.json

# &#x20;  - personas/bot.config.json

# &#x20;  - realai/bot/boot.py

# &#x20;  - realai/bot/\_\_init\_\_.py

# 

# 2\. personas/realai\_bot.json must contain:

# &#x20;  - id: realai-bot-default

# &#x20;  - name: RealAI Bot

# &#x20;  - provider: RealAI

# &#x20;  - memory\_namespace: persona\_realai\_bot

# &#x20;  - system\_prompt: canonical RealAI system prompt (single string)

# 

# 3\. personas/bot.config.json must enforce:

# &#x20;  - routing.default = "local"

# &#x20;  - only\_providers = \["local","realai"]

# &#x20;  - disable all cloud providers

# &#x20;  - fallback\_backend = "llama.cpp"

# &#x20;  - local\_model = "realai-default"

# 

# 4\. realai/bot/boot.py must implement:

# &#x20;  - DEFAULT\_REALAI\_PROMPT

# &#x20;  - load\_prompt()

# &#x20;  - inject\_system(messages)

# &#x20;  - register\_default\_bot() using PersonaSwitcher + IdentityManager

# &#x20;  - guard so boot runs once on startup

# 

# 5\. Patch identity.py and realai/identity.py:

# &#x20;  - Replace "You are a helpful AI assistant." with DEFAULT\_REALAI\_PROMPT.

# 

# 6\. Patch core/inference/chat\_pipeline.py:

# &#x20;  - After \_augment\_messages and before chat\_backend.generate:

# &#x20;    augmented\_messages = \_ensure\_realai\_system(augmented\_messages)

# 

# 7\. Patch apps/api/routes/chat.py:

# &#x20;  - If req.model is missing or cloud-like, coerce to "realai-default".

# &#x20;  - Never construct cloud clients.

# 

# 8\. Patch apps/frontend/src/app/api/chat/route.ts:

# &#x20;  - Force model to "realai-default".

# &#x20;  - Remove cloud model IDs.

# &#x20;  - Identity = RealAI.

# 

# 9\. Patch apps/frontend/src/app/page.tsx:

# &#x20;  - UI title and labels = RealAI Bot.

# 

# 10\. Patch router.py and realai/router.py:

# &#x20;  - Change fallback provider from "openai" to "local".

# &#x20;  - Add select\_realai\_bot\_provider() returning \["local","realai"].

# 

# 11\. Patch providers.yaml:

# &#x20;  - local.enabled = true

# &#x20;  - disable all cloud providers

# 

# 12\. Add config flag REALAI\_BOT\_LOCAL\_ONLY=1 to force local-only provider detection.

# 

# 13\. Add tests verifying:

# &#x20;  - RealAI system prompt injection

# &#x20;  - No cloud routing

# &#x20;  - Persona registration idempotent

# &#x20;  - Provider selection returns only local/realai

# 

# Goal:

# RealAI Bot becomes the default persona for all chat paths (API, GUI, CLI, frontend), using only local RealAI inference.

# 

