"""Eval harness for datasets and live native-model inference."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


def evaluate_instruction_dataset(dataset_path=None) -> Dict[str, Any]:
    """Count dataset rows for a lightweight eval summary."""
    path = (
        Path(dataset_path)
        if dataset_path
        else Path(__file__).resolve().parents[1] / "datasets" / "processed" / "train.jsonl"
    )
    if not path.exists():
        return {"status": "empty", "examples": 0, "dataset_path": str(path)}
    examples = len([line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])
    return {"status": "ready", "examples": examples, "dataset_path": str(path)}


def evaluate_native_server(
    base_url: str = "http://127.0.0.1:8000",
    model_id: str = "realai-1.0-instruct",
) -> Dict[str, Any]:
    """Ping /v1/models and optional chat for a RealAI-owned model id."""
    base = base_url.rstrip("/")
    summary: Dict[str, Any] = {"base_url": base, "model_id": model_id}

    try:
        with urllib.request.urlopen(f"{base}/v1/models", timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        models = payload.get("data") or payload.get("models") or []
        summary["models_listed"] = len(models)
        entry = next((m for m in models if m.get("id") == model_id), None)
        if entry:
            summary["weights_ready"] = entry.get("weights_ready", entry.get("weight_status"))
    except urllib.error.URLError as exc:
        summary["status"] = "server_unreachable"
        summary["error"] = str(exc)
        return summary

    body = json.dumps(
        {
            "model": model_id,
            "messages": [{"role": "user", "content": "Reply with the word: realai"}],
            "max_tokens": 32,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            chat = json.loads(resp.read().decode("utf-8"))
        text = (
            chat.get("choices", [{}])[0]
            .get("message", {})
            .get("content", chat.get("choices", [{}])[0].get("text", ""))
        )
        summary["status"] = "ok"
        summary["sample_reply"] = (text or "")[:500]
    except urllib.error.HTTPError as exc:
        summary["status"] = "chat_failed"
        summary["http_status"] = exc.code
        summary["error"] = exc.read().decode("utf-8", errors="replace")[:500]
    except urllib.error.URLError as exc:
        summary["status"] = "chat_unreachable"
        summary["error"] = str(exc)
    return summary


def main():
    """CLI entrypoint for eval."""
    print(json.dumps({"dataset": evaluate_instruction_dataset()}, indent=2))
    return evaluate_instruction_dataset()


if __name__ == "__main__":
    main()
