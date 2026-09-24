#!/usr/bin/env python3
"""
RealAI Ability Catalog (Phase 5F)
=================================
Canonical map of technical-rundown capabilities -> LIVE / PARTIAL / CODE / GOLD / MISSING / SOFT.

Feeds self-heal coverage, /v1/capabilities, keyword learning for deeper DDS-3 scans,
and self-improve training samples. External machine roots (C:\\tools\\realai, Users trees,
historical backups, Atomic Fizz, .realai runtime, etc.) are registered via era_map.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_PKG = Path(__file__).resolve().parent
_ROOT = _PKG.parent
_SCAN = _ROOT / "scan_results"
_TRAIN = _ROOT / "training" / "data"

_STATUS_WEIGHT = {
    "LIVE": 1.0,
    "PARTIAL": 0.55,
    "SOFT": 0.35,
    "CODE": 0.25,
    "GOLD": 0.15,
    "STUB": 0.1,
    "MISSING": 0.0,
}

RUNDOWN_ABILITIES: List[Dict[str, Any]] = [
    {
        "id": "chat_completion",
        "name": "Chat completion",
        "pillar": "core_ai",
        "keywords": ["chat", "chat/completions", "completions", "messages"],
        "status": "LIVE",
        "live_path": "POST /v1/chat/completions",
        "modules": ["realai/v3_orchestrator.py"],
    },
    {
        "id": "text_generation",
        "name": "Text generation",
        "pillar": "core_ai",
        "keywords": ["text generation", "generate", "completion"],
        "status": "LIVE",
        "live_path": "POST /v1/chat/completions",
        "modules": ["realai/v3_orchestrator.py"],
    },
    {
        "id": "image_generation",
        "name": "Image generation",
        "pillar": "core_ai",
        "keywords": ["image", "images/generations", "dall-e", "image gen"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.image_generation (local Pillow PNG; no API key)",
        "modules": ["abilities/image_generation.py", "realai/local_media.py"],
        "gold_paths": [
            r"C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS\backend\lib\grok.js",
            r"C:\tools\realai\commands\image.js",
        ],
    },
    {
        "id": "video_generation",
        "name": "Video generation",
        "pillar": "core_ai",
        "keywords": ["video", "video generation", "video.js"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.video_generation (local animated GIF; no API key)",
        "modules": ["abilities/video_generation.py", "realai/local_media.py"],
        "gold_paths": [
            r"C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS\backend\lib\grok.js",
            r"C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS\scripts\test_video_generation.js",
            r"C:\tools\realai\commands\video.js",
        ],
    },
    {
        "id": "image_analysis",
        "name": "Image analysis (vision)",
        "pillar": "core_ai",
        "keywords": ["vision", "image analysis", "multimodal", "image_url"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.image_analysis (local Pillow; no API key)",
        "modules": ["abilities/image_analysis.py", "realai/local_media.py"],
    },
    {
        "id": "code_generation",
        "name": "Code generation",
        "pillar": "core_ai",
        "keywords": ["code generation", "coding", "qwen2.5-coder"],
        "status": "LIVE",
        "live_path": "POST /v1/chat/completions (model)",
        "modules": ["realai/v3_orchestrator.py", "realai/coding_agent.py"],
    },
    {
        "id": "code_execution",
        "name": "Code execution",
        "pillar": "core_ai",
        "keywords": ["code execution", "sandbox", "exec", "tool_calls", "agent_tools", "executor"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute (execute_code sandbox)",
        "modules": [
            "realai/v3_orchestrator.py",
            "realai/tools.py",
            "agent_tools",
            "realai/agent_tools_gold",
            "realai-core/agent_tools",
            "recovered/from_agent_tools/agent_tools",
            "imports/external/agent_tools_gold",
        ],
        "gold_paths": [
            r"C:\Users\tsmit\Documents\GitHub\realai\realai-core\agent_tools",
            r"C:\Users\tsmit\realai\agent-tools\agent-tools-main",
        ],
    },
    {
        "id": "embeddings",
        "name": "Embeddings",
        "pillar": "core_ai",
        "keywords": ["embeddings", "embedding", "vector", "realai-embed"],
        "status": "LIVE",
        "live_path": "POST /v1/embeddings",
        "modules": [
            "realai/lambda_embeddings_audio.py",
            "realai/server/embeddings_backend.py",
            "realai/v3_orchestrator.py",
        ],
    },
    {
        "id": "audio_transcription",
        "name": "Audio transcription (ASR)",
        "pillar": "core_ai",
        "keywords": ["transcription", "asr", "whisper", "speech-to-text", "audio/transcriptions"],
        "status": "LIVE",
        "live_path": "POST /v1/audio/transcriptions + ability.audio_transcription (local Vosk)",
        "modules": ["abilities/audio_transcription.py", "realai/voice", "C:/models/vosk"],
    },
    {
        "id": "audio_speech",
        "name": "Audio speech (TTS)",
        "pillar": "core_ai",
        "keywords": ["tts", "text-to-speech", "audio/speech", "speech synthesis"],
        "status": "LIVE",
        "live_path": "POST /v1/audio/speech + ability.audio_speech (realai.voice / Windows SAPI / Kokoro)",
        "modules": ["abilities/audio_speech.py", "realai/voice/provider.py", "realai/voice/tts_engine.py"],
    },
    {
        "id": "translation",
        "name": "Translation",
        "pillar": "core_ai",
        "keywords": ["translation", "translate", "multilingual"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.translation → local Hive chat",
        "modules": ["abilities/translation.py", "realai/local_media.py"],
    },
    {
        "id": "web_research",
        "name": "Web research & scraping",
        "pillar": "advanced",
        "keywords": ["web research", "scraping", "research", "web_search"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute web_research",
        "modules": ["abilities/web_search.py"],
        "gold_paths": [r"C:\tools\realai\commands\research.js"],
    },
    {
        "id": "task_automation",
        "name": "Task automation & infra ops",
        "pillar": "advanced",
        "keywords": ["automation", "infra", "self-heal", "self_heal", "task"],
        "status": "LIVE",
        "live_path": "POST /v1/self-heal/* + tools self_heal_*",
        "modules": ["abilities/task_automation.py"],
    },
    {
        "id": "voice_streaming",
        "name": "Voice interaction (streaming)",
        "pillar": "advanced",
        "keywords": ["voice", "streaming voice", "asr", "tts conversation"],
        "status": "LIVE",
        "live_path": "ability.voice_streaming oneshot (local TTS↔Hive chat) + optional WS",
        "modules": ["abilities/voice_streaming.py", "abilities/audio_speech.py", "realai/voice"],
    },
    {
        "id": "business_planning",
        "name": "Business planning",
        "pillar": "advanced",
        "keywords": ["business planning", "business plan"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.business_planning → local Hive chat",
        "modules": ["abilities/business_planning.py", "realai/local_media.py"],
    },
    {
        "id": "therapy_counseling",
        "name": "Therapy & counseling",
        "pillar": "advanced",
        "keywords": ["therapy", "counseling", "counsellor"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.therapy_counseling → local Hive chat",
        "modules": ["abilities/therapy_counseling.py", "realai/local_media.py"],
    },
    {
        "id": "web3_integration",
        "name": "Web3 integration",
        "pillar": "advanced",
        "keywords": ["web3", "solana", "evm", "wallet", "defi", "nft", "smart contract"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.web3_integration + core.tools.web3",
        "modules": [
            "core/web3",
            "core/tools/web3.py",
            "abilities/web3_integration.py",
            "realai/api/state.py",
        ],
        "gold_paths": [
            r"C:\tools\realai\commands\web3.js",
            r"C:\tools\realai\plugins\solana.js",
            r"C:\tools\realai\plugins\trading.js",
        ],
    },
    {
        "id": "coach",
        "name": "RackUp professional coach",
        "pillar": "advanced",
        "keywords": ["coach", "practice plan", "mental game", "pre-match", "pyramid coach", "rackup coach"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.coach + rackup_invoke",
        "modules": [
            "abilities/rackup/coach.py",
            "plugins/rackup_coach/abilities/coach.py",
            "plugins/rackup_coach",
        ],
    },
    {
        "id": "shot_of_the_day",
        "name": "Shot of the Day",
        "pillar": "advanced",
        "keywords": ["shot of the day", "sotd", "practice drill", "rackup sotd"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.shot_of_the_day + rackup_invoke",
        "modules": [
            "abilities/rackup/shot_of_the_day.py",
            "plugins/rackup_coach/abilities/shot_of_the_day.py",
            "plugins/rackup_coach",
        ],
    },
    {
        "id": "rating_update",
        "name": "Post-match rating update",
        "pillar": "advanced",
        "keywords": ["rating update", "glicko", "glicko2", "post-match rating", "skill update"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.rating_update + rackup_invoke",
        "modules": [
            "abilities/rackup/rating_update.py",
            "plugins/rackup_coach/abilities/rating_update.py",
            "plugins/rackup_coach",
        ],
    },
    {
        "id": "tournament",
        "name": "Tournament / league insights",
        "pillar": "advanced",
        "keywords": ["tournament", "bracket", "league insights", "pyramid event", "rackup tournament"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.tournament + rackup_invoke",
        "modules": [
            "abilities/rackup/tournament.py",
            "plugins/rackup_coach/abilities/tournament.py",
            "plugins/rackup_coach",
        ],
    },
    {
        "id": "ledger_audit",
        "name": "ROC ledger audit",
        "pillar": "advanced",
        "keywords": ["ledger audit", "money audit", "session audit", "season audit", "roc ledger"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.ledger_audit + rackup_invoke",
        "modules": [
            "abilities/rackup/ledger_audit.py",
            "plugins/rackup_coach/abilities/ledger_audit.py",
            "plugins/rackup_coach",
        ],
    },
    {
        "id": "matchmaking",
        "name": "Matchmaking advice",
        "pillar": "advanced",
        "keywords": ["matchmaking", "opponent fit", "rating band", "pairing"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.matchmaking + rackup_invoke",
        "modules": [
            "abilities/rackup/matchmaking.py",
            "plugins/rackup_coach/abilities/matchmaking.py",
            "plugins/rackup_coach",
        ],
    },
    {
        "id": "hall_context",
        "name": "hall context",
        "pillar": "advanced",
        "keywords": ["hall context", "rackup", "hall_context"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.hall_context + rackup_invoke",
        "modules": ["abilities/rackup/hall_context.py", "plugins/rackup_coach/abilities/hall_context.py", "plugins/rackup_coach"],
    },
    {
        "id": "league_validate",
        "name": "league validate",
        "pillar": "advanced",
        "keywords": ["league validate", "rackup", "league_validate"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.league_validate + rackup_invoke",
        "modules": ["abilities/rackup/league_validate.py", "plugins/rackup_coach/abilities/league_validate.py", "plugins/rackup_coach"],
    },
    {
        "id": "moderation",
        "name": "moderation",
        "pillar": "advanced",
        "keywords": ["moderation", "rackup", "moderation"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.moderation + rackup_invoke",
        "modules": ["abilities/rackup/moderation.py", "plugins/rackup_coach/abilities/moderation.py", "plugins/rackup_coach"],
    },
    {
        "id": "money_anomaly",
        "name": "money anomaly",
        "pillar": "advanced",
        "keywords": ["money anomaly", "rackup", "money_anomaly"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.money_anomaly + rackup_invoke",
        "modules": ["abilities/rackup/money_anomaly.py", "plugins/rackup_coach/abilities/money_anomaly.py", "plugins/rackup_coach"],
    },
    {
        "id": "payout_sanity",
        "name": "payout sanity",
        "pillar": "advanced",
        "keywords": ["payout sanity", "rackup", "payout_sanity"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.payout_sanity + rackup_invoke",
        "modules": ["abilities/rackup/payout_sanity.py", "plugins/rackup_coach/abilities/payout_sanity.py", "plugins/rackup_coach"],
    },
    {
        "id": "pyramid_rules",
        "name": "pyramid rules",
        "pillar": "advanced",
        "keywords": ["pyramid rules", "rackup", "pyramid_rules"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.pyramid_rules + rackup_invoke",
        "modules": ["abilities/rackup/pyramid_rules.py", "plugins/rackup_coach/abilities/pyramid_rules.py", "plugins/rackup_coach"],
    },
    {
        "id": "rating_convert",
        "name": "rating convert",
        "pillar": "advanced",
        "keywords": ["rating convert", "rackup", "rating_convert"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.rating_convert + rackup_invoke",
        "modules": ["abilities/rackup/rating_convert.py", "plugins/rackup_coach/abilities/rating_convert.py", "plugins/rackup_coach"],
    },
    {
        "id": "rating_intel",
        "name": "rating intel",
        "pillar": "advanced",
        "keywords": ["rating intel", "rackup", "rating_intel"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.rating_intel + rackup_invoke",
        "modules": ["abilities/rackup/rating_intel.py", "plugins/rackup_coach/abilities/rating_intel.py", "plugins/rackup_coach"],
    },
    {
        "id": "player_card_sync",
        "name": "unified player card sync",
        "pillar": "advanced",
        "keywords": ["player card", "player_card_sync", "unified player card", "fargo", "rackup"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.player_card_sync + rackup_invoke",
        "modules": ["abilities/rackup/player_card_sync.py", "plugins/rackup_coach/abilities/player_card_sync.py", "plugins/rackup_coach"],
    },
    {
        "id": "sotd_contribute",
        "name": "sotd contribute",
        "pillar": "advanced",
        "keywords": ["sotd contribute", "rackup", "sotd_contribute"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.sotd_contribute + rackup_invoke",
        "modules": ["abilities/rackup/sotd_contribute.py", "plugins/rackup_coach/abilities/sotd_contribute.py", "plugins/rackup_coach"],
    },
    {
        "id": "video_analysis",
        "name": "video analysis",
        "pillar": "advanced",
        "keywords": ["video analysis", "rackup", "video_analysis"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.video_analysis + rackup_invoke",
        "modules": ["abilities/rackup/video_analysis.py", "plugins/rackup_coach/abilities/video_analysis.py", "plugins/rackup_coach"],
    },
    {
        "id": "desktop_lambda_chat",
        "name": "desktop lambda chat",
        "pillar": "advanced",
        "keywords": ["desktop lambda chat", "rackup", "desktop_lambda_chat"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.desktop_lambda_chat",
        "modules": ["abilities/desktop_lambda_chat.py", "modules/desktop_unique/lambda_chat.py"],
    },
    {
        "id": "desktop_lambda_image",
        "name": "desktop lambda image",
        "pillar": "advanced",
        "keywords": ["desktop lambda image", "rackup", "desktop_lambda_image"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.desktop_lambda_image",
        "modules": ["abilities/desktop_lambda_image.py", "modules/desktop_unique/lambda_image.py"],
    },
    {
        "id": "desktop_lambda_video",
        "name": "desktop lambda video",
        "pillar": "advanced",
        "keywords": ["desktop lambda video", "rackup", "desktop_lambda_video"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.desktop_lambda_video",
        "modules": ["abilities/desktop_lambda_video.py", "modules/desktop_unique/lambda_video.py"],
    },
    {
        "id": "desktop_lambda_advanced",
        "name": "desktop lambda advanced",
        "pillar": "advanced",
        "keywords": ["desktop lambda advanced", "rackup", "desktop_lambda_advanced"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.desktop_lambda_advanced",
        "modules": ["abilities/desktop_lambda_advanced.py", "modules/desktop_unique/lambda_advanced.py"],
    },
    {
        "id": "overmind_runner",
        "name": "overmind runner",
        "pillar": "advanced",
        "keywords": ["overmind runner", "rackup", "overmind_runner"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.overmind_runner",
        "modules": ["abilities/overmind_runner.py", "modules/agents_advanced/overmind_runner.py"],
    },
    {
        "id": "code_engineer_agent",
        "name": "code engineer agent",
        "pillar": "advanced",
        "keywords": ["code engineer agent", "rackup", "code_engineer_agent"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.code_engineer_agent",
        "modules": ["abilities/code_engineer_agent.py", "modules/agents_advanced/code_engineer_agent.py"],
    },
    {
        "id": "deep_promote",
        "name": "Deep promote (named roots + nests)",
        "pillar": "advanced",
        "keywords": ["deep promote", "nested gold", "thin wrap", "promote deep", "function diff"],
        "status": "LIVE",
        "live_path": "abilities/deep_promote.py + craft /promote",
        "modules": [
            "abilities/deep_promote.py",
            "scripts/deep_promote_scan.py",
            "scripts/deep_promote_wire.py",
            "realai/cli/craft.py",
        ],
    },
    {
        "id": "hierarchical_specialists",
        "name": "hierarchical_specialists",
        "pillar": "advanced",
        "keywords": ["hierarchical specialists", "hierarchical_specialists"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.hierarchical_specialists",
        "modules": ["abilities/hierarchical_specialists.py", "core/agents/agents.py", "core/agents/tools.py"],
    },
    {
        "id": "approval_store",
        "name": "approval_store",
        "pillar": "advanced",
        "keywords": ["approval store", "approval_store"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.approval_store",
        "modules": ["abilities/approval_store.py", "realai/plugins/tools/approval_store.py"],
    },
    {
        "id": "device_selector",
        "name": "device_selector",
        "pillar": "advanced",
        "keywords": ["device selector", "device_selector"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute device_selector + ability.device_selector",
        "modules": ["abilities/device_selector.py", "realai/plugins/tools/device_selector.py"],
    },
    {
        "id": "code_engineer_cli",
        "name": "Code Engineer CLI",
        "pillar": "advanced",
        "keywords": ["code engineer cli", "patch apply", "git apply", "code_engineer_cli"],
        "status": "LIVE",
        "live_path": "abilities/code_engineer_cli.py + realai.plugins.tools.code_engineer_cli",
        "modules": [
            "abilities/code_engineer_cli.py",
            "realai/plugins/tools/code_engineer_cli.py",
            "agent_tools/agents_impl/code_engineer_agent.py",
        ],
    },
    {
        "id": "harden_repos",
        "name": "Harden repos",
        "pillar": "ops",
        "keywords": ["harden repos", "repo hardening", "security workflow", "dependabot"],
        "status": "LIVE",
        "live_path": "abilities/harden_repos.py + realai.plugins.tools.harden_repos",
        "modules": ["abilities/harden_repos.py", "realai/plugins/tools/harden_repos.py"],
    },
    {
        "id": "rollout_all_repos",
        "name": "Rollout all repos",
        "pillar": "ops",
        "keywords": ["rollout repos", "rollout_all_repos", "agentx pack", "repo upgrade"],
        "status": "LIVE",
        "live_path": "abilities/rollout_all_repos.py + realai.plugins.tools.rollout_all_repos",
        "modules": ["abilities/rollout_all_repos.py", "realai/plugins/tools/rollout_all_repos.py"],
    },
    {
        "id": "quarantine_reconstruct",
        "name": "Quarantine reconstruct",
        "pillar": "ops",
        "keywords": ["quarantine", "reconstruct", "delta candidates", "promote quarantine"],
        "status": "LIVE",
        "live_path": "abilities/quarantine_reconstruct.py",
        "modules": ["abilities/quarantine_reconstruct.py", "realai/abilities/quarantine_reconstruct.py"],
    },
    {
        "id": "plugin_system",
        "name": "Plugin system",
        "pillar": "advanced",
        "keywords": ["plugin", "plugin_marketplace", "PluginManifest", "PluginDiscovery"],
        "status": "LIVE",
        "live_path": "plugins/rackup_coach + POST tools rackup_invoke",
        "modules": [
            "realai/plugin_marketplace.py",
            "plugins/rackup_coach",
            "abilities/rackup",
            "realai/abilities/registry.json",
        ],
        "gold_paths": [r"C:\tools\realai\core\plugins.js", r"C:\tools\realai\plugins"],
    },
    {
        "id": "learn_git",
        "name": "Git-learn (offline packet + coach stub)",
        "pillar": "advanced",
        "keywords": ["learn_git", "git-learn", "/learn", "learning packet", "learned plugin"],
        "status": "LIVE",
        "live_path": "python -m realai.learn_git --all-branches + Craft /learn (no heal)",
        "modules": [
            "realai/learn_git.py",
            "realai/learn/pipeline.py",
            "abilities/learn_git.py",
            "realai/plugins",
        ],
    },
    {
        "id": "memory_learning",
        "name": "Memory & persistent learning",
        "pillar": "advanced",
        "keywords": ["memory", "memory_engine", "vector memory", "persistent learning", "chroma"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.memory_learning + aura_memory + hive_memory + chat inject",
        "modules": ["abilities/memory_learning.py", "abilities/hive_memory.py", "realai/aura_memory.py", "realai/v3_orchestrator.py"],
        "gold_paths": [
            r"C:\Users\tsmit\realai\realai_memory",
            r"C:\Users\tsmit\.realai\conversations.db",
        ],
    },
    {
        "id": "self_reflection",
        "name": "Chain-of-thought + self-reflection",
        "pillar": "advanced",
        "keywords": ["self_reflect", "critique", "self-reflection", "chain-of-thought"],
        "status": "LIVE",
        "live_path": "POST /v1/self-improve/evaluate",
        "modules": ["realai/self_improvement.py", "realai/critique.py"],
    },
    {
        "id": "knowledge_synthesis",
        "name": "Knowledge synthesis",
        "pillar": "advanced",
        "keywords": ["knowledge graph", "knowledge_graph", "world_model", "synthesis"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.knowledge_synthesis + knowledge_graph + world_model",
        "modules": ["abilities/knowledge_synthesis.py", "realai/knowledge_graph.py", "realai/world_model.py"],
    },
    {
        "id": "multi_agent",
        "name": "Multi-agent orchestration",
        "pillar": "advanced",
        "keywords": [
            "multi-agent", "planner", "worker", "critic", "synthesizer", "agentx", "agent_id",
            "hierarchical_agent", "orchestrator", "shared memory", "rise_system",
        ],
        "status": "LIVE",
        "live_path": "POST /v1/multi-agent/run + chat multi_agent=true + GET /v1/agents",
        "modules": [
            "realai/agent_runtime/",
            "agents/agentx",
            "realai/v3_runtime_bridge.py",
        ],
        "gold_paths": [
            r"C:\Users\tsmit\.agentx",
            r"C:\Users\tsmit\OneDrive\Desktop\realai-orchestration",
            r"C:\Users\tsmit\OneDrive\Desktop\realai_agent",
            r"C:\realai\recovered\from_desktop\realai-orchestration",
            r"C:\realai\recovered\from_desktop\realai_agent",
        ],
    },
    {
        "id": "game_world",
        "name": "Game-world integration (Atomic Fizz)",
        "pillar": "advanced",
        "keywords": [
            "atomic fizz", "npc", "quest", "overseer", "pip-boy", "game world", "wasteland",
            "dialogue-engine", "dungeon-generator", "local-overseer", "world-event",
            "omnibrain", "world-brain", "vault77",
        ],
        "status": "LIVE",
        "live_path": "POST tools game_world|omnibrain|world_brain + MCP vault77",
        "modules": [
            "abilities/game_world.py",
            "abilities/omnibrain.py",
            "abilities/world_brain.py",
            "realai/atomic_fizz/world_brain.py",
            "realai/mcp_vault77.py",
            "realai/plugins/atomic_fizz_realai",
            "realai/plugins/atomic_fizz_realai/engines_gold",
            "realai/plugins/atomic_fizz_realai/media",
            "realai/plugins/atomic_fizz_realai/plugin_manifest.json",
        ],
        "gold_paths": [
            r"C:\tools\realai\plugins\overseer.js",
            r"C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS",
            r"C:\Users\tsmit\ATOMIC-FIZZ-CAPS-OLD",
            r"C:\Users\tsmit\atomic-fizz-backup-2026-05-30",
            r"C:\Unwrenchable",
            r"C:\realai\recovered\from_atomic_fizz\backend_realai",
            r"C:\realai\plugins\atomic_fizz_realai",
        ],
    },
    {
        "id": "organs_hive",
        "name": "Synthetic organs hive",
        "pillar": "advanced",
        "keywords": [
            "organs", "organ pipeline", "synthetic organs", "frontal-cortex",
            "hippocampus", "organs_task",
        ],
        "status": "LIVE",
        "live_path": "POST tools organs_task + abilities/organs_hive.py",
        "modules": [
            "abilities/organs_hive.py",
            "modules/organs",
            "modules/organs/request_path.py",
        ],
    },
    {
        "id": "observability_self_improve",
        "name": "Observability, auditing, self-improvement",
        "pillar": "advanced",
        "keywords": ["observability", "audit", "self_improvement", "self-improve", "self_heal"],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.observability_self_improve + /v1/self-heal/* + /v1/self-improve/*",
        "modules": ["abilities/observability_self_improve.py", "realai/self_heal.py", "realai/self_improvement.py", "realai/audit.py"],
    },
    {
        "id": "local_inference",
        "name": "Local inference (Vulkan / GGUF)",
        "pillar": "local_intelligence",
        "keywords": ["vulkan", "gguf", "llama-server", "qwen", "local model"],
        "status": "LIVE",
        "live_path": "http://127.0.0.1:8080 via orchestrator",
        "modules": ["realai/v3_orchestrator.py"],
        "gold_paths": [r"C:\llama-vulkan", r"C:\llama", r"C:\Users\tsmit\.realai\models"],
    },
    {
        "id": "training_pipeline",
        "name": "Training + fine-tune pipeline",
        "pillar": "model_family",
        "keywords": ["finetune", "training", "dataset", "lora", "realai-1.0"],
        "status": "LIVE",
        "live_path": "GET /v1/training/* GET /v1/lora",
        "modules": ["realai/training", "training/data", "realai/recovery_registry.py"],
        "gold_paths": [
            r"C:\Users\tsmit\Downloads\realai_finetune_dataset.jsonl",
            r"C:\models\checkpoints_lora",
        ],
    },
    {
        "id": "lora_adapters",
        "name": "Recovered PEFT LoRA adapters",
        "pillar": "model_family",
        "keywords": ["lora", "peft", "adapter", "checkpoints_lora", "finetune adapter"],
        "status": "LIVE",
        "live_path": "GET /v1/lora",
        "modules": ["realai/recovery_registry.py", "realai/model_catalog.py"],
        "gold_paths": [
            r"C:\models\checkpoints_lora",
            r"recovered/from_kilo_restore/_discovered/checkpoints_lora",
        ],
    },
    {
        "id": "kilo_recovery",
        "name": "Kilo-era gold recovery wiring",
        "pillar": "ops",
        "keywords": ["kilo", "recovery", "git clean", "realai2", "checkpoints_lora"],
        "status": "LIVE",
        "live_path": "GET /v1/recovery",
        "modules": ["realai/recovery_registry.py", "realai/v3_orchestrator.py"],
    },
    {
        "id": "frontend_ui",
        "name": "Next.js operator UI",
        "pillar": "product",
        "keywords": ["frontend", "next.js", "chat ui", "settings drawer"],
        "status": "LIVE",
        "live_path": "http://127.0.0.1:3000",
        "modules": ["apps/frontend"],
        "gold_paths": [r"C:\temp\realai_ui.html"],
    },
    {
        "id": "cli_surface",
        "name": "CLI surface (tools install)",
        "pillar": "product",
        "keywords": ["cli", "realai.cmd", "commands", "realai help"],
        "status": "LIVE",
        "live_path": "bin/realai*.cmd + realai.cli.craft (in-tree; not C:\\tools\\realai husk)",
        "modules": ["bin/realai.cmd", "realai/cli/craft.py", "abilities/cli_surface.py"],
        "gold_paths": [r"C:\tools\realai"],
        "status_note": "C:\\tools\\realai is a hollow husk (14/20 files 0 B) — SKIP fold; names only (see scan_results/TOOLS_CLI_FOLD.md)",
    },
    {
        "id": "hive_governance",
        "name": "Hive governance",
        "pillar": "enterprise",
        "keywords": [
            "hive governance",
            "governance",
            "enterprise",
            "agentic os",
            "hominis",
            "hominis_enterprise",
        ],
        "status": "LIVE",
        "live_path": "POST /v1/tools/execute ability.hive_governance (local agents + coverage)",
        "modules": ["abilities/hive_governance.py", "realai/agent_activity.py"],
        "status_note": "Local Hive governance — agent roster, profiles, coverage; no external API. Formerly hominis_enterprise.",
        "aliases": ["hominis_enterprise"],
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_wsl_or_native(p: str) -> List[Path]:
    """Return candidate Path objects for a Windows or POSIX path."""
    out: List[Path] = []
    if not p:
        return out
    out.append(Path(p))
    if p.startswith("C:\\") or p.startswith("C:/"):
        out.append(Path("/mnt/c/" + p[3:].replace("\\", "/")))
    elif p.startswith("/mnt/c/"):
        out.append(Path("C:\\" + p[len("/mnt/c/") :].replace("/", "\\")))
    return out


def path_exists(p: str) -> bool:
    for c in to_wsl_or_native(p):
        try:
            if c.exists():
                return True
        except OSError:
            pass
    return False


def first_existing(p: str) -> Optional[Path]:
    for c in to_wsl_or_native(p):
        try:
            if c.exists():
                return c
        except OSError:
            pass
    return None


def load_era_map() -> Dict[str, Any]:
    p = _SCAN / "era_map.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def external_scan_roots() -> List[Dict[str, Any]]:
    era = load_era_map()
    roots: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for p in era.get("external_scan_roots_for_abilities") or []:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        roots.append({
            "path": p,
            "exists": path_exists(p),
            "source": "external_scan_roots_for_abilities",
        })

    for e in era.get("eras") or []:
        role = str(e.get("role") or "")
        if role in ("noise", "authority", "staging"):
            continue
        for p in e.get("paths") or []:
            if not isinstance(p, str):
                continue
            if not (p.startswith("C:\\") or p.startswith("C:/") or p.startswith("/")):
                continue
            key = p.lower()
            if key in seen:
                continue
            seen.add(key)
            roots.append({
                "path": p,
                "exists": path_exists(p),
                "era_id": e.get("id"),
                "role": role,
                "notes": e.get("notes"),
                "source": "era_map.eras",
            })
    return roots


def load_ability_inventory() -> Dict[str, Any]:
    p = _SCAN / "dds3_ability_inventory.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_learned_keywords() -> Dict[str, Any]:
    p = _SCAN / "ability_keywords_learned.json"
    if not p.is_file():
        return {"version": 1, "keywords": [], "patterns": [], "sources": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "keywords": [], "patterns": [], "sources": []}


def _token_keywords_from_inventory(inv: Dict[str, Any]) -> List[str]:
    kws: List[str] = []
    for key in ("multi_era_abilities", "only_outside_clean", "single_era_sample"):
        for row in inv.get(key) or []:
            if isinstance(row, dict):
                t = row.get("token")
                if t and isinstance(t, str) and len(t) >= 3:
                    kws.append(t)
            elif isinstance(row, str):
                kws.append(row)
    return kws


def scan_tools_cli_surface() -> Dict[str, Any]:
    """Prefer in-tree bin/craft CLI; retain hollow C:\\tools\\realai as husk metadata only."""
    in_tree_bin = _ROOT / "bin"
    in_tree_cmds = []
    if in_tree_bin.is_dir():
        for f in sorted(in_tree_bin.glob("realai*.cmd")):
            try:
                size = f.stat().st_size
            except OSError:
                size = -1
            in_tree_cmds.append({"name": f.stem, "bytes": size, "stub": size == 0, "source": "bin"})

    husk = first_existing(r"C:\tools\realai")
    surface: Dict[str, Any] = {
        "path": str(_ROOT / "bin") if in_tree_cmds else r"C:\tools\realai",
        "exists": bool(in_tree_cmds) or husk is not None,
        "commands": list(in_tree_cmds),
        "plugins": [],
        "core": [],
        "entrypoints": [],
        "ability_hints": [c["name"] for c in in_tree_cmds],
        "in_tree": {
            "bin": str(in_tree_bin),
            "craft": str(_ROOT / "realai" / "cli" / "craft.py"),
            "realai_cmd": str(_ROOT / "realai.cmd"),
            "command_count": len(in_tree_cmds),
        },
        "husk": {
            "path": r"C:\tools\realai",
            "exists": husk is not None,
            "note": "hollow husk — SKIP fold; names only (scan_results/TOOLS_CLI_FOLD.md)",
        },
    }
    craft = _ROOT / "realai" / "cli" / "craft.py"
    if craft.is_file():
        try:
            surface["entrypoints"].append({"name": "craft.py", "bytes": craft.stat().st_size, "source": "in_tree"})
        except OSError:
            surface["entrypoints"].append({"name": "craft.py", "source": "in_tree"})
    root_cmd = _ROOT / "realai.cmd"
    if root_cmd.is_file():
        try:
            surface["entrypoints"].append({"name": "realai.cmd", "bytes": root_cmd.stat().st_size, "source": "in_tree"})
        except OSError:
            surface["entrypoints"].append({"name": "realai.cmd", "source": "in_tree"})

    if husk is not None:
        for sub, key in (("commands", "commands"), ("plugins", "plugins"), ("core", "core")):
            d = husk / sub
            if not d.is_dir():
                continue
            for f in sorted(d.iterdir()):
                if f.suffix.lower() != ".js":
                    continue
                try:
                    size = f.stat().st_size
                except OSError:
                    size = -1
                row = {"name": f.stem, "bytes": size, "stub": size == 0, "source": "husk"}
                # keep husk names in plugins/core; do not override in-tree commands list
                if key == "commands":
                    surface.setdefault("husk_commands", []).append(row)
                else:
                    surface[key].append(row)
                    if key == "plugins":
                        surface["ability_hints"].append(f.stem)
    return surface


def _enrich_status_from_disk(entry: Dict[str, Any]) -> Dict[str, Any]:
    e = dict(entry)
    modules = e.get("modules") or []
    gold = e.get("gold_paths") or []
    found_mod = []
    for m in modules:
        if (_ROOT / m).exists() or path_exists(m):
            found_mod.append(m)
    found_gold = [g for g in gold if path_exists(g)]
    e["modules_found"] = found_mod
    e["gold_found"] = found_gold
    if e.get("status") == "CODE" and found_gold and not found_mod:
        e["status"] = "GOLD"
        e["status_note"] = "modules not on authority path; gold/external surface present"
    if e.get("status") in ("STUB", "MISSING") and found_gold:
        if e.get("status") == "MISSING":
            e["status"] = "GOLD"
        e["status_note"] = "CLI/gold scaffold present (may be empty stub files)"
    return e




def load_wired_learned_abilities() -> List[Dict[str, Any]]:
    """Abilities created by POST /v1/learn/wire (PARTIAL / learned)."""
    path = _ROOT / "realai" / "catalog" / "learned" / "wired_abilities.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = data.get("abilities") if isinstance(data, dict) else data
    out: List[Dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        aid = str(row.get("id") or "").strip()
        if not aid:
            continue
        out.append(
            {
                "id": aid,
                "name": str(row.get("name") or aid),
                "status": "PARTIAL",
                "learned": True,
                "keywords": list(row.get("keywords") or ["learned", "wire"]),
                "modules": list(row.get("modules") or []),
                "live_path": str(row.get("live_path") or f"POST /v1/tools/execute ability.{aid}"),
                "status_note": "Learned bridge via /v1/learn/wire — wraps plugin invoke, no foreign copy",
            }
        )
    return out


def build_catalog() -> Dict[str, Any]:
    inv = load_ability_inventory()
    inv_tokens = _token_keywords_from_inventory(inv)
    learned = load_learned_keywords()
    tools_surface = scan_tools_cli_surface()
    external = external_scan_roots()

    abilities: List[Dict[str, Any]] = []
    for seed in RUNDOWN_ABILITIES:
        e = _enrich_status_from_disk(seed)
        matched = []
        kws_l = [k.lower() for k in (e.get("keywords") or [])]
        for tok in inv_tokens:
            tl = tok.lower()
            if any(k in tl or tl in k for k in kws_l):
                matched.append(tok)
        e["inventory_tokens"] = sorted(set(matched))[:40]
        e["inventory_hit_count"] = len(set(matched))
        abilities.append(e)

    # Learned wires (PARTIAL) — never overwrite rundown ids
    existing_ids = {str(a.get("id") or "") for a in abilities}
    for row in load_wired_learned_abilities():
        rid = str(row.get("id") or "")
        if not rid or rid in existing_ids:
            continue
        abilities.append(row)
        existing_ids.add(rid)

    by_status: Dict[str, int] = {}
    weighted = 0.0
    for a in abilities:
        st = a.get("status") or "MISSING"
        by_status[st] = by_status.get(st, 0) + 1
        weighted += _STATUS_WEIGHT.get(st, 0.0)
    n = max(len(abilities), 1)
    coverage = {
        "ability_count": len(abilities),
        "by_status": by_status,
        "weighted_score": round(weighted / n, 4),
        "weighted_pct": round(100.0 * weighted / n, 1),
        "live_count": by_status.get("LIVE", 0),
        "partial_count": by_status.get("PARTIAL", 0),
        "code_or_gold": (
            by_status.get("CODE", 0)
            + by_status.get("GOLD", 0)
            + by_status.get("STUB", 0)
        ),
        "missing_count": by_status.get("MISSING", 0) + by_status.get("SOFT", 0),
        "note": (
            "weighted_pct is honesty score vs technical rundown, "
            "NOT verify_matrix pass counts (stack health only)"
        ),
    }

    return {
        "meta": {
            "version": 1,
            "phase": "5F",
            "generated_at": _utc(),
            "root": str(_ROOT),
            "source": (
                "technical_rundown + dds3_ability_inventory + era_map external roots "
                "+ C:\\tools\\realai + machine gold scan"
            ),
        },
        "coverage": coverage,
        "abilities": abilities,
        "external_gold_roots": external,
        "external_roots_exist": sum(1 for r in external if r.get("exists")),
        "external_roots_total": len(external),
        "tools_cli_surface": tools_surface,
        "inventory_summary": {
            "multi_era": (inv.get("counts") or {}).get("multi_era"),
            "only_outside_clean": (inv.get("counts") or {}).get("only_outside_clean"),
            "unique_tokens_meta": (inv.get("meta") or {}).get("unique_tokens"),
        },
        "learned_keywords_count": len(learned.get("keywords") or []),
        "endpoints": {
            "catalog": "GET /v1/capabilities",
            "self_heal_abilities": "GET /v1/self-heal/abilities",
            "learn": "POST /v1/self-heal/learn-keywords",
        },
    }


def save_catalog(catalog: Optional[Dict[str, Any]] = None) -> Path:
    cat = catalog or build_catalog()
    _SCAN.mkdir(parents=True, exist_ok=True)
    out = _SCAN / "ability_catalog.json"
    out.write_text(json.dumps(cat, indent=2), encoding="utf-8")

    md_path = _ROOT / "docs" / "ABILITY_SURFACE.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    cov = cat["coverage"]
    lines = [
        "# RealAI Ability Surface (Phase 5F)",
        "",
        f"Generated: `{cat['meta']['generated_at']}`",
        "",
        f"**Coverage vs technical rundown:** **{cov['weighted_pct']}%** weighted "
        f"({cov['live_count']} LIVE, {cov['partial_count']} PARTIAL, "
        f"{cov['code_or_gold']} CODE/GOLD/STUB, {cov['missing_count']} MISSING/SOFT)",
        "",
        "> `verify_v3_matrix` pass counts = stack health, not full product ability completeness.",
        "",
        f"## External gold roots ({cat.get('external_roots_exist')}/{cat.get('external_roots_total')} present)",
        "",
    ]
    for r in cat.get("external_gold_roots") or []:
        mark = "OK" if r.get("exists") else "MISSING"
        extra = r.get("era_id") or r.get("role") or r.get("source") or ""
        lines.append(f"- `{mark}` `{r.get('path')}` — {extra}")
    tools = cat.get("tools_cli_surface") or {}
    lines += [
        "",
        "## C:\\tools\\realai CLI surface",
        "",
        f"- exists: **{tools.get('exists')}**",
        f"- commands: {', '.join(c['name'] for c in tools.get('commands') or []) or '(none)'}",
        f"- plugins: {', '.join(p['name'] for p in tools.get('plugins') or []) or '(none)'}",
        "",
        "## Abilities",
        "",
        "| ID | Name | Status | Live path |",
        "|----|------|--------|-----------|",
    ]
    for a in cat.get("abilities") or []:
        lines.append(
            f"| `{a['id']}` | {a['name']} | **{a['status']}** | `{a.get('live_path') or '—'}` |"
        )
    lines += [
        "",
        "## Keyword learning",
        "",
        "Discover / learn-keywords merges inventory tokens + CLI surface + rundown keywords "
        "+ external roots into `scan_results/ability_keywords_learned.json` so DDS-3 ability "
        "scans go deeper each cycle. Self-improve training samples: `training/data/ability_surface.jsonl`.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return out


def learn_keywords_from_scans(also_tools_cli: bool = True) -> Dict[str, Any]:
    inv = load_ability_inventory()
    prev = load_learned_keywords()
    prev_set: Set[str] = set(prev.get("keywords") or [])
    new_kws: Set[str] = set()
    sources: List[str] = list(prev.get("sources") or [])

    for a in RUNDOWN_ABILITIES:
        for k in a.get("keywords") or []:
            new_kws.add(k.lower().strip())
        new_kws.add(a["id"].replace("_", " "))
    sources.append("technical_rundown")

    for t in _token_keywords_from_inventory(inv):
        if re.match(r"^[A-Za-z][A-Za-z0-9_\-]{2,64}$", t):
            new_kws.add(t)
    if inv:
        sources.append("dds3_ability_inventory")

    for row in inv.get("only_outside_clean") or []:
        tok = row.get("token") if isinstance(row, dict) else row
        if tok:
            new_kws.add(str(tok))

    tools_surface: Dict[str, Any] = {}
    if also_tools_cli:
        tools_surface = scan_tools_cli_surface()
        for h in tools_surface.get("ability_hints") or []:
            new_kws.add(str(h).lower())
        sources.append(r"C:\tools\realai")

    # External root path basenames as soft keywords
    for r in external_scan_roots():
        if r.get("exists"):
            base = Path(str(r["path"]).replace("\\", "/")).name.lower()
            if base and base not in ("tsmit", "users", "downloads", "temp"):
                new_kws.add(base.replace("-", "_"))
    sources.append("era_map_external_roots")

    # Filenames under tools CLI already done; also historic names
    for extra in (
        "overseer", "solana", "trading", "render", "agentx", "atomic_fizz",
        "wasteland", "real_fin", "agent_tools", "hive", "chroma", "rag_memory",
    ):
        new_kws.add(extra)

    patterns: List[Dict[str, str]] = []
    for kw in sorted(new_kws):
        if " " in kw or "/" in kw:
            patterns.append({"kind": "phrase", "keyword": kw, "regex": re.escape(kw)})
        elif re.match(r"^[A-Za-z_][A-Za-z0-9_\-]*$", kw):
            token = kw.replace("-", "_")
            patterns.append({
                "kind": "token",
                "keyword": kw,
                "regex": rf"\b{re.escape(token)}\b",
            })

    added = sorted(new_kws - prev_set)
    merged = sorted(prev_set | new_kws)
    payload = {
        "version": int(prev.get("version") or 1) + (1 if added else 0),
        "updated_at": _utc(),
        "keywords": merged,
        "patterns": patterns[:800],
        "added_this_cycle": added,
        "added_count": len(added),
        "total_count": len(merged),
        "sources": sorted(set(sources)),
        "tools_cli_surface": tools_surface if also_tools_cli else prev.get("tools_cli_surface"),
        "external_roots": external_scan_roots(),
        "note": "Loaded by scanners/dds3_missing_files.py for deeper ability scans",
    }
    _SCAN.mkdir(parents=True, exist_ok=True)
    (_SCAN / "ability_keywords_learned.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return payload


def emit_training_samples(max_samples: int = 100) -> Dict[str, Any]:
    cat = build_catalog()
    lines_out: List[str] = []
    for a in cat.get("abilities") or []:
        status = a.get("status")
        name = a.get("name")
        live = a.get("live_path")
        if status == "LIVE":
            content = (
                f"RealAI ability `{a['id']}` ({name}) is LIVE. "
                f"Use it via: {live}. Keywords: {', '.join(a.get('keywords') or [])}."
            )
        elif status == "PARTIAL":
            content = (
                f"RealAI ability `{a['id']}` ({name}) is PARTIAL on the v3 path. "
                f"Live entry: {live or 'limited'}. Full surface still being promoted from gold/code."
            )
        else:
            content = (
                f"RealAI ability `{a['id']}` ({name}) is currently {status}. "
                f"Gold/modules: {a.get('gold_found') or a.get('modules_found') or 'search inventory'}. "
                f"Do not claim it is fully production-ready."
            )
        rec = {
            "messages": [
                {"role": "user", "content": f"What can RealAI do for: {name}?"},
                {"role": "assistant", "content": content},
            ]
        }
        lines_out.append(json.dumps(rec))
        if len(lines_out) >= max_samples:
            break

    tools = cat.get("tools_cli_surface") or {}
    if tools.get("exists"):
        cmds = [c["name"] for c in tools.get("commands") or []]
        plugs = [p["name"] for p in tools.get("plugins") or []]
        lines_out.append(json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": "Where is the RealAI CLI install and what does it declare?",
                },
                {
                    "role": "assistant",
                    "content": (
                        f"External CLI gold is at C:\\tools\\realai. "
                        f"Commands (many stubs): {', '.join(cmds)}. "
                        f"Plugins: {', '.join(plugs)}. "
                        f"Treat as ability surface blueprint; promote into C:\\RealAI-clean authority."
                    ),
                },
            ]
        }))

    # External roots lesson
    present = [r["path"] for r in (cat.get("external_gold_roots") or []) if r.get("exists")]
    lines_out.append(json.dumps({
        "messages": [
            {
                "role": "user",
                "content": "Where else on this machine should RealAI look for missing abilities?",
            },
            {
                "role": "assistant",
                "content": (
                    "External gold roots for self-improve / self-heal ability discovery include: "
                    + "; ".join(present[:20])
                    + ". Never bulk-merge; catalog, learn keywords, promote uniques only."
                ),
            },
        ]
    }))

    _TRAIN.mkdir(parents=True, exist_ok=True)
    out = _TRAIN / "ability_surface.jsonl"
    out.write_text("\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8")
    return {
        "ok": True,
        "path": str(out),
        "samples": len(lines_out),
        "coverage_pct": cat["coverage"]["weighted_pct"],
    }


def coverage_summary() -> Dict[str, Any]:
    cat = build_catalog()
    return {
        "coverage": cat["coverage"],
        "ability_count": cat["coverage"]["ability_count"],
        "external_roots_exist": cat.get("external_roots_exist"),
        "external_roots_total": cat.get("external_roots_total"),
        "tools_cli": {
            "path": r"C:\tools\realai",
            "exists": (cat.get("tools_cli_surface") or {}).get("exists"),
            "commands": [c["name"] for c in (cat.get("tools_cli_surface") or {}).get("commands") or []],
            "plugins": [p["name"] for p in (cat.get("tools_cli_surface") or {}).get("plugins") or []],
        },
        "generated_at": cat["meta"]["generated_at"],
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Build RealAI ability catalog + learn keywords")
    ap.add_argument("--learn", action="store_true")
    ap.add_argument("--train-samples", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    do_all = args.all or (not args.learn and not args.train_samples)

    path = save_catalog()
    cov = coverage_summary()
    print(f"[ability_catalog] wrote {path}")
    print(
        f"[ability_catalog] coverage {cov['coverage']['weighted_pct']}% "
        f"({cov['coverage']['live_count']} LIVE) "
        f"external_roots {cov.get('external_roots_exist')}/{cov.get('external_roots_total')}"
    )
    tools = cov.get("tools_cli") or {}
    print(
        f"[ability_catalog] C:\\tools\\realai exists={tools.get('exists')} "
        f"cmds={tools.get('commands')} plugs={tools.get('plugins')}"
    )
    if args.learn or args.all or do_all:
        learned = learn_keywords_from_scans()
        print(
            f"[ability_catalog] learned keywords total={learned['total_count']} "
            f"added={learned['added_count']}"
        )
    if args.train_samples or args.all or do_all:
        tr = emit_training_samples()
        print(f"[ability_catalog] training samples {tr['samples']} -> {tr['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
