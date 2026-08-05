import os
import json
import re
import hashlib

ROOT = "C:\\realai"
OUT = "C:\\realai\\scan_results\\fs1_full_spectrum_manifest.json"

# -----------------------------
# FULL SPECTRUM KEYWORD SET
# -----------------------------
KEYWORDS = [

    # Memory / RAG / Vector DB
    "memory","episodic","semantic","working memory","long-term","cache","persist",
    "checkpoint","snapshot","serialize","deserialize","recall","retrieve",
    "embedding","embeddings","vector","vectorstore","vector_store","vector db",
    "dimension","encode","encoder","decode","decoder","faiss","textfaiss",
    "chromadb","chroma_db","sqlite","pinecone","qdrant","weaviate",
    "hybrid search","retriever","indexing","rerank","reranker",

    # Training / LoRA / GPU / Local inference
    "train","training","finetune","fine-tune","lora","textlora","lora_adapter",
    "peft","adapter","fine_tuning","diffusers","scheduler","schedulers",
    "ollama","vllm","llama.cpp","huggingface","transformers","bitsandbytes",
    "quantize","quantization","directml","vulkan","cuda","rocm","gpu_balancer",
    "model_name","base_model",

    # Agents / Multi-agent / Workflow
    "agent","agents","multiagent","textmultiagent","crewai","langgraph","autogen",
    "workflow","orchestrator","executor","coordinator","delegator","handover",
    "task_queue","priority",

    # Plugins / MCP / VS Code / Connectors
    "plugin","plugins","textmcp","mcp","model_context_protocol","vscode","vs_code",
    "extension","manifest","activation","command","contributes","provider",
    "tree_provider","webview","panel","context_menu","status_bar",

    # Self-improvement / Evolution
    "self_improve","textself_improve","self-improve","self_improvement",
    "meta_learn","metalearning","evolver","evolutionary","bootstrap","self_boot",
    "bootstrapper","continual","lifelong",

    # Autonomy / Safety / Governance
    "autonomy","autonomous","self-heal","self-repair","self-upgrade",
    "self-maintain","self-optimization","self-regulate","self-govern",
    "self-governance","self-correct","self-align","self-evaluate","safety",
    "safe","guardrail","constraint","limit","policy","rule","filter","gate",
    "gating","permission","auth","authorize","restrict","restriction",

    # Watchdog / Supervisor / Fallback
    "watchdog","monitor","monitoring","supervisor","controller","governor",
    "fallback","failsafe","recovery","retry","backoff","degradation","graceful",
    "resilience","heartbeat","healthcheck","diagnostic","probe","status",

    # Worldmodel / NPC / Quest / Game logic
    "quest","quests","textquest","lore","dialogue","dialog","npc","npcs","persona",
    "personality","behavior_tree","btree","fsm","finite_state","pda",
    "programmable_data","c_nft","cnft",

    # Backend / Infra / Databases
    "fastify","express","nextjs","vercel","render.com","postgres","postgis",
    "pgvector","redis","celery","docker","dockerfile","compose","kubernetes","helm",

    # Solana / Crypto / On-chain
    "solana","textsolana","solders","anchor","program_id","pda","bonding_curve",
    "token_mint","zk_compression",

    # Telemetry / Observability
    "telemetry","texttelemetry","sentry","prometheus","grafana","opentelemetry",
    "trace","tracing","span","instrumentation",

    # RealAI-specific subsystems
    "realai_plugin","realai_mcp","realai_vscode","realai_lora","realai_ollama",
    "realai_solana","realai_worldmodel","realai_hivemind","hive_mind"
]

# -----------------------------
# FILE EXTENSIONS TO SCAN
# -----------------------------
EXTENSIONS = [
    ".py",".js",".ts",".json",".yaml",".yml",".toml",".ini",".cfg",
    ".md",".mdx",".txt",".rst",".html",".css",".vue",".svelte",
    ".sh",".bash",".ps1",".bat",".cmd",".ipynb",".sql",".db",".sqlite",
    ".env"
]

# -----------------------------
# HASHING
# -----------------------------
def hash_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return None

# -----------------------------
# CONTEXT EXTRACTION
# -----------------------------
def extract_context(lines, index, radius=10):
    start = max(0, index - radius)
    end = min(len(lines), index + radius)
    return "\n".join(lines[start:end])

# -----------------------------
# SCAN FILE
# -----------------------------
def scan_file(path):
    hits = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            text = "".join(lines).lower()
    except:
        return hits

    for kw in KEYWORDS:
        if kw.lower() in text:
            for i, line in enumerate(lines):
                if kw.lower() in line.lower():
                    hits.append({
                        "keyword": kw,
                        "line_number": i + 1,
                        "context": extract_context(lines, i)
                    })
    return hits

# -----------------------------
# WALK DIRECTORY
# -----------------------------
def walk(root):
    manifest = []
    for dirpath, dirs, files in os.walk(root):
        for file in files:
            if any(file.lower().endswith(ext) for ext in EXTENSIONS):
                full = os.path.join(dirpath, file)
                results = scan_file(full)
                if results:
                    manifest.append({
                        "file": full,
                        "hash": hash_file(full),
                        "hits": results
                    })
    return manifest

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    manifest = walk(ROOT)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[FS-1] Full Spectrum Scan Complete → {OUT}")
