"""Extract training JSONL from self-builder sessions and agent logs.

CANONICAL (realai/core/training). Merged 2026-10-16 from realai/training/extract_from_agent_tools.py (sessions ->
instruction samples, dedupe; that path is now a shim), the 35-line starter that used to live here (closed_loop imported
``extract_all_training_sources`` from it and failed), and training/extract_from_agent_tools.py (load_json,
normalize_agent_tool_log: raw agent-tool JSON logs -> messages).
"""

from __future__ import annotations

import json
from pathlib import Path
import glob
from typing import Any, Dict, List, Optional

OUT_DIR = Path(__file__).resolve().parents[2] / "datasets" / "processed"  # realai/datasets/processed (unchanged)
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_json(path) -> Optional[Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def normalize_agent_tool_log(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a raw agent-tool log entry into a training sample (from training/extract_from_agent_tools.py)."""
    messages: List[Dict[str, Any]] = []
    if "user" in entry:
        messages.append({"role": "user", "content": entry["user"]})
    if "agent" in entry:
        messages.append({"role": "assistant", "content": entry["agent"]})
    if "tool_input" in entry:
        messages.append({"role": "assistant", "content": f"<tool:{entry.get('tool_name', 'unknown')}>{entry['tool_input']}"})
    if "tool_output" in entry:
        messages.append({"role": "tool", "content": entry["tool_output"]})
    if "final" in entry:
        messages.append({"role": "assistant", "content": entry["final"]})
    return {"messages": messages}


def agent_tool_log_samples(input_root: str | Path | None = None) -> List[Dict[str, Any]]:
    root = Path(input_root) if input_root else _repo_root() / "realai" / "logs" / "agent-tools"
    out: List[Dict[str, Any]] = []
    for file in sorted(glob.glob(str(root / "*.json"))):
        raw = load_json(file)
        if isinstance(raw, dict):
            sample = normalize_agent_tool_log(raw)
            if len(sample["messages"]) >= 2:
                sample["source"] = "agent_tool_log"
                out.append(sample)
    return out


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


def extract_all_training_sources(output_root: str | Path | None = None,
                                 input_root: str | Path | None = None) -> Dict[str, Any]:
    output_dir = Path(output_root) if output_root else OUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    samples: List[Dict[str, Any]] = []
    sessions_path = output_dir / "self_builder_sessions.jsonl"
    samples.extend(sessions_to_instruction_samples(_read_jsonl(sessions_path)))
    samples.extend(agent_tool_log_samples(input_root))

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


# --- Recovered 2026-10-17 from git (nested repo realai/.learn_cache/realai, unreachable commit c6237d4f
# "Add structured realai package layout"). The old extractor also wrote code-diff and memory-summary pairs;
# the current one only writes instructions.jsonl. Opt-in only: extract_all_training_sources()/main() are unchanged.
_ARTIFACT_DATASET_FILENAMES = {
    'code_pairs': 'code_pairs.jsonl',
    'memory_pairs': 'memory_pairs.jsonl',
}


def _load_json_records(path):
    suffix = path.suffix.lower()
    if suffix == '.jsonl':
        records = []
        with path.open('r', encoding='utf-8') as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return records
    if suffix == '.json':
        with path.open('r', encoding='utf-8') as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            return payload
        return [payload]
    if suffix in ('.patch', '.diff', '.txt'):
        return [{'content': path.read_text(encoding='utf-8')}]
    return []


def _collect_records(input_root):
    categories = {
        'logs': [],
        'memory': [],
        'traces': [],
        'diffs': [],
    }
    patterns = {
        'logs': ('**/*log*.json', '**/*log*.jsonl'),
        'memory': ('**/*memory*.json', '**/*memory*.jsonl'),
        'traces': ('**/*trace*.json', '**/*trace*.jsonl'),
        'diffs': ('**/*.diff', '**/*.patch', '**/*diff*.txt'),
    }
    for category, globs in patterns.items():
        for pattern in globs:
            for path in sorted(input_root.glob(pattern)):
                categories[category].extend(_load_json_records(path))
    return categories


def _instruction_examples(records):
    examples = []
    for item in records.get('logs', []) + records.get('traces', []):
        prompt = item.get('prompt') or item.get('task') or item.get('query') or item.get('input')
        response = item.get('response') or item.get('output') or item.get('result')
        if not prompt or not response:
            continue
        examples.append({
            'messages': [
                {'role': 'user', 'content': str(prompt)},
                {'role': 'assistant', 'content': str(response)},
            ],
            'source': item.get('source', 'agent-tools'),
        })
    return examples


def _code_examples(records):
    examples = []
    for item in records.get('diffs', []):
        diff_text = item.get('content', '').strip()
        if not diff_text:
            continue
        examples.append({
            'instruction': 'Apply the following code change faithfully.',
            'input': diff_text,
            'output': diff_text,
            'source': 'code-diff',
        })
    return examples


def _memory_examples(records):
    examples = []
    for item in records.get('memory', []):
        raw_content = item.get('content') or item.get('memory') or item.get('summary') or item.get('input')
        summary = item.get('summary') or item.get('output') or item.get('result')
        if not raw_content or not summary:
            continue
        examples.append({
            'input': str(raw_content),
            'summary': str(summary),
            'source': item.get('source', 'memory'),
        })
    return examples


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + '\n')


def extract_code_and_memory_pairs(input_root, output_root=None) -> Dict[str, Any]:
    """Opt-in: write code_pairs.jsonl / memory_pairs.jsonl from agent-tool artifacts under input_root (read-only)."""
    in_dir = Path(input_root)
    output_dir = Path(output_root) if output_root else OUT_DIR
    records = _collect_records(in_dir)
    rows = {'code_pairs': _code_examples(records), 'memory_pairs': _memory_examples(records)}
    out: Dict[str, Any] = {}
    for key, name in _ARTIFACT_DATASET_FILENAMES.items():
        _write_jsonl(output_dir / name, rows[key])
        out[key] = {'path': str(output_dir / name), 'rows': len(rows[key])}
    return out


def extract_agent_tool_data(input_root=None, output_root=None):
    """Backward-compatible entry: merge all sources into instructions.jsonl."""
    return extract_all_training_sources(output_root=output_root, input_root=input_root)


def main():
    result = extract_all_training_sources()
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()