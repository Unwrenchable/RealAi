"""Takes raw extracted JSONL and builds train/val splits."""

from pathlib import Path
import json
import random

DATA_DIR = Path(__file__).resolve().parents[1] / 'datasets' / 'processed'


def build_dataset_bundle(input_root=None, output_root=None):
    """Build train/val splits from instructions.jsonl."""
    data_dir = Path(output_root) if output_root else DATA_DIR
    source_dir = Path(input_root) if input_root else data_dir
    source = source_dir / 'instructions.jsonl'
    if not source.exists():
        from .extract_from_agent_tools import extract_agent_tool_data
        extract_agent_tool_data(output_root=str(data_dir))
    lines = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines() if line.strip()]
    random.Random(42).shuffle(lines)
    split = int(len(lines) * 0.9)
    if split <= 0 or split >= len(lines):
        train = lines
        val = []
    else:
        train = lines[:split]
        val = lines[split:]
    train_path = data_dir / 'train.jsonl'
    val_path = data_dir / 'val.jsonl'
    train_path.write_text('\n'.join(json.dumps(item) for item in train), encoding='utf-8')
    val_path.write_text('\n'.join(json.dumps(item) for item in val), encoding='utf-8')
    return {
        'datasets': {
            'train': {'path': str(train_path), 'rows': len(train)},
            'val': {'path': str(val_path), 'rows': len(val)},
        }
    }


def main():
    """CLI entrypoint for dataset building."""
    return build_dataset_bundle()


if __name__ == '__main__':
    main()
