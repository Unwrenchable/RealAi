"""Extract training JSONL from self-builder sessions and agent logs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

OUT_DIR = Path(__file__).resolve().parents[1] / "datasets" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def sessions_to_instruction_samples(sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    samples: List[Dict[str, Any]] = []
    for session in sessions:
        task = session.get("task") or ""
        messages = session.get("messages")
        if isinstance(messages, list) and len(messages) >= 2:
            samples.append({"messages": messages, "source": "self_builder_session"})
            continue
        result = session.get("result") or {}
        summary = result.get("summary") or ""
        trace = result.get("trace") or []
        if not task:
            continue
        assistant_parts = []
        for step in trace:
            if step.get("assistant"):
                assistant_parts.append(str(step["assistant"])[:2000])
            if step.get("tool"):
                assistant_parts.append(
                    "TOOL: {0}\nARGS: {1}".format(step["tool"], json.dumps(step.get("args") or {}))
                )
        if summary:
            assistant_parts.append("DONE: " + summary)
        if not assistant_parts:
            continue
        samples.append(
            {
                "messages": [
                    {"role": "user", "content": task},
                    {"role": "assistant", "content": "\n\n".join(assistant_parts)[:12000]},
                ],
                "source": "self_builder_trace",
            }
        )
    return samples


def extract_all_training_sources(output_root: str | Path | None = None) -> Dict[str, Any]:
    output_dir = Path(output_root) if output_root else OUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    samples: List[Dict[str, Any]] = []
    sessions_path = output_dir / "self_builder_sessions.jsonl"
    samples.extend(sessions_to_instruction_samples(_read_jsonl(sessions_path)))

    # Starter + legacy path
    samples.extend(
        [
            {
                "messages": [
                    {"role": "user", "content": "How do I run RealAI locally without API keys?"},
                    {
                        "role": "assistant",
                        "content": (
                            "Start python -m realai.server.app, set REALAI_API_URL, "
                            "then realai-build or python -m realai.closed_loop."
                        ),
                    },
                ],
                "source": "seed",
            }
        ]
    )

    seen = set()
    unique: List[Dict[str, Any]] = []
    for item in samples:
        key = json.dumps(item.get("messages", []), sort_keys=True)[:500]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    out_path = output_dir / "instructions.jsonl"
    with out_path.open("w", encoding="utf-8") as handle:
        for sample in unique:
            handle.write(json.dumps(sample) + "\n")

    return {
        "instructions": str(out_path),
        "rows": len(unique),
        "sessions_file": str(sessions_path),
        "sessions_rows": len(_read_jsonl(sessions_path)),
    }


def extract_agent_tool_data(input_root=None, output_root=None):
    """Backward-compatible entry: merge all sources into instructions.jsonl."""
    return extract_all_training_sources(output_root=output_root)


def main():
    result = extract_all_training_sources()
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()