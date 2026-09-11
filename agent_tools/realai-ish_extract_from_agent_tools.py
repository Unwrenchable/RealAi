"""Extracts data from agent-tools logs and memory into JSONL for training."""

from pathlib import Path
import json

OUT_DIR = Path(__file__).resolve().parents[1] / 'datasets' / 'processed'
OUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_agent_tool_data(input_root=None, output_root=None):
    """Write a small starter instruction dataset."""
    output_dir = Path(output_root) if output_root else OUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    samples = [
        {
            'messages': [
                {'role': 'user', 'content': 'Explain vector databases.'},
                {'role': 'assistant', 'content': 'A vector database stores embeddings for semantic retrieval.'}
            ]
        }
    ]
    out_path = output_dir / 'instructions.jsonl'
    with out_path.open('w', encoding='utf-8') as handle:
        for sample in samples:
            handle.write(json.dumps(sample) + '\n')
    return {'instructions': str(out_path)}


def main():
    """CLI entrypoint for extraction."""
    return extract_agent_tool_data()


if __name__ == '__main__':
    main()
