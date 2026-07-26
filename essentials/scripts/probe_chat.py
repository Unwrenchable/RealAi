import requests

m = [
    {"role": "system", "content": "Use TOOL/ARGS format."},
    {"role": "user", "content": "List realai folder"},
    {"role": "assistant", "content": 'TOOL: list_dir\nARGS: {"target_directory": "realai"}'},
    {
        "role": "user",
        "content": 'OBSERVATION: {"entries": [{"name": "self_builder.py"}]}\nNow read self_builder.py limit 5',
    },
]
r = requests.post(
    "http://127.0.0.1:8000/v1/chat/completions",
    json={"model": "qwen-coder-7b", "messages": m, "max_tokens": 256},
    timeout=300,
)
r.raise_for_status()
data = r.json()
print("backend:", data.get("backend"))
print(data["choices"][0]["message"]["content"][:400])