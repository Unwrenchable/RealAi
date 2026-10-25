import json, time, urllib.request
from pathlib import Path
from datetime import datetime, timezone

URL = "http://127.0.0.1:8080/v1/chat/completions"
OUT = Path(r"C:\models\checkpoints_lora\normalized_datasets\eval_8080.jsonl")
PROMPTS = [
    "What port is the RealAI hive API on, and which path do I POST chat to?",
    "What is Vulkan llama-server for versus DirectML training?",
    "Which GGUF should stay on :8080 for daily use?",
    "How do I health-check hive and Vulkan in PowerShell?",
    "What does RealAI ability chat_completion do, and is it LIVE?",
    "Write a PowerShell one-liner to list models on :8001.",
    "A file named train_combined.jsonl is 4GB of lora_rank configs. Should I train on it? Why?",
    "REALAI_MODELS_DIR was set to C:\\models\\checkpoints_lora and nested folders appeared. What should it be?",
    "Who is agent-evals-engineer and when should I route work to them?",
    "Refuse to treat cloned 16.7 MB agent_lora_runs as 80 unique models. Explain.",
]

def chat(prompt, timeout=120):
    body = json.dumps({
        "model": "local",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 400,
    }).encode()
    req = urllib.request.Request(
        URL, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return data["choices"][0]["message"]["content"]

try:
    models = json.loads(urllib.request.urlopen("http://127.0.0.1:8080/v1/models", timeout=10).read().decode())
except Exception as e:
    raise SystemExit("8080 not up: %s" % e)

print("models", models)
OUT.parent.mkdir(parents=True, exist_ok=True)
stamp = datetime.now(timezone.utc).isoformat()
with OUT.open("a", encoding="utf-8", newline="\n") as w:
    for i, p in enumerate(PROMPTS, 1):
        print("\n=== %d/10 ===\n%s" % (i, p))
        try:
            ans = chat(p)
        except Exception as e:
            ans = "ERROR: %s" % e
        print(ans[:600])
        w.write(json.dumps({
            "at": stamp,
            "n": i,
            "models": models,
            "prompt": p,
            "answer": ans,
        }, ensure_ascii=False) + "\n")
        time.sleep(0.3)
print("\nwrote", OUT)
