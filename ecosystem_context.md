# RealAI Ecosystem Context

## Integration Points

## Memory Chunks

## Instruction Pairs

**Q:** Explain the RealAI hive runtime and how the orchestrator fits in.
**A:** RealAI runs a local hive: Vulkan llama-server on :8080 serving a GGUF model, and the hive gateway on :8001 via `python -m realai.v3_orchestrator`. The orchestrator handles chat, tools, multi-agent coordination, abilities, plugins (including RackUp coach), organs, and self-heal loops. Cloud twin is `realai.api_server`. Live branch is live/realai-clean-20260911. All useful code lives inside the single realai/ package, not version folders.

**Q:** How does Atomic Fizz Caps integrate with an Overseer AI and what blockchain features does it have?
**A:** Atomic Fizz (Vault-77 Wasteland GPS) is a Fallout-themed real-world GPS scavenger game. The Overseer Terminal is an AI assistant (Hugging Face Mixtral or fallback) for status, quests, lore, weather, and threat assessment. It includes claim system, battle, crafting, factions, perks, gear/NFTs, Scavenger Exchange, Nuke recycling, Wormhole bridge across 35+ chains, and a Twitter Gamemaker bot. FIZZ is an SPL token on Solana with Phantom wallet support. Game events can webhook to the Overseer Bot.

**Q:** Describe the RackUp pool players app core features and how RealAI can support it.
**A:** RackUp is a mobile-first social-competitive pool app with hall pulse, matchmaking/go-live, money matches/tournaments/leagues, friends and live chat, hall check-ins, daily coach drills, match memories, and player profiles/badges. RealAI already has RackUp-related plugins (coach, ratings, SOTD). Foreign-repo mode and the orchestrator can code against the NestJS/TypeScript backend and Vite frontend, and memory chunks of the codebase let agents reason about matchmaking and league rules.

**Q:** What does the Overseer Bot AI do and how does it connect to Atomic Fizz?
**A:** Overseer Bot AI is a Vault-77 themed Twitter bot (Flask + APScheduler). It posts Fallout-style content, promotes atomicfizzcaps.xyz, monitors SOL/BTC/ETH prices with alerts, scans tokens for honeypots/rugs, and receives game event webhooks (/overseer-event) for perks, quests, swaps, NFTs, level-ups, and location claims. AI responses prefer xAI/Grok then OpenAI/HuggingFace. It runs as a single gunicorn worker on Render.

**Q:** How can agent-tools be used with the RealAI ecosystem?
**A:** agent-tools provides an agentx CLI for agent registry, capability checks (safe/balanced/power profiles), real-time execution dashboard, multi-agent workflows, and multi-repo rollout of .agentx packs. It can import agency-style markdown agents, enforce required tools, and harden repos. RealAI agents and .github/agents can be registered or checked with it, and the rollout scripts can apply consistent agent configs across Unwrenchable repos.

**Q:** What is the recommended way to add new abilities or plugins to RealAI?
**A:** New runtime code goes in realai/<pillar>/ (orchestration, core, plugins, voice, training). New operator-facing ability goes in product-root abilities/<name>.py AND a row in realai/ability_catalog.py. New plugin is a package under realai/plugins/<name>/ with a manifest. Never create v4/ or version folders. Recovery snapshots stay on recovery/* branches until scanners/promote_gold.py validates them.

**Q:** How do I run RealAI in a foreign repo or any random project folder?
**A:** Install once with the global script so REALAI_HOME points to C:\RealAI-clean and commands are on PATH. Start the stack (realai-stack) if the GPU hive is not already running. Then cd into the foreign folder and run realai or realai-code "your task". REALAI_WORKSPACE defaults to the current directory. Slash commands /list /read /grep /write operate on that folder. Models, promote logic, and logs stay in HOME. Use realai -C D:\OtherApp chat "..." to override the workspace without changing directory.

**Q:** What stays local to the foreign project vs what stays in RealAI HOME?
**A:** The foreign project (cwd) is the workspace for file tools (/list /read /write /grep), coding sessions, and heal diagnostics. Everything else stays in REALAI_HOME: models (Vulkan GGUFs), curated promote/archive of recovered files, audit logs under logs/state, the hive orchestrator, plugins, and ability catalog. No runtime dependency is dumped into the foreign repo.

**Q:** Give the daily flow for using RealAI across multiple foreign repos.
**A:** Once per machine session: realai-stack (Vulkan :8080 + orchestrator :8001). Then for any project: cd into it, run realai for interactive craft chat, realai-code "specific change", realai-heal for diagnostics, and realai-health to check endpoints. Repeat for the next foreign repo. The same hive and models serve every folder.

**Q:** How do I run RealAI in a foreign repo or any folder?
**A:** Install once with scripts/install_global.ps1 so realai is on PATH and REALAI_HOME is set. Then cd into any project and run realai, realai-code, realai-heal, or realai-selfheal. REALAI_WORKSPACE defaults to cwd. Models stay in REALAI_HOME. Use realai -C D:\OtherApp chat "..." to target a different folder. Slash commands (/list /read /write /heal) act on the current workspace.

**Q:** What should RealAI know when coding inside one of my other repos?
**A:** Use the ecosystem memory chunks. RealAI should know Atomic Fizz (GPS scavenger + Solana CAPS + Overseer), RackUp (pool matchmaking/leagues), overseer-bot-ai (Twitter + crypto webhooks), FizzSwap/FizzChain, Cue-guard (NFC cue storage), agent-tools registry, and the foreign-repo mode itself so it can operate in any folder without losing context.