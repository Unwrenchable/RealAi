"""Thin wrapper around HuggingFace / TRL / Axolotl."""

from pathlib import Path


def build_finetune_plan(data_dir=None):
    """Return the train/val paths for a future fine-tune job."""
    dataset_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parents[1] / 'datasets' / 'processed'
    train_path = dataset_dir / 'train.jsonl'
    val_path = dataset_dir / 'val.jsonl'
    return {
        'status': 'ready',
        'train_path': str(train_path),
        'val_path': str(val_path),
    }


def main():
    """CLI entrypoint for the fine-tune stub."""
    plan = build_finetune_plan()
    print('[realai] Fine-tune stub. Train: {0}, Val: {1}'.format(plan['train_path'], plan['val_path']))
    return plan


if __name__ == '__main__':
    main()
