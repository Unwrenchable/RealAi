"""Simple eval harness stub."""

from pathlib import Path


def evaluate_instruction_dataset(dataset_path=None):
    """Count dataset rows for a lightweight eval summary."""
    path = Path(dataset_path) if dataset_path else Path(__file__).resolve().parents[1] / 'datasets' / 'processed' / 'train.jsonl'
    if not path.exists():
        return {'status': 'empty', 'examples': 0, 'dataset_path': str(path)}
    examples = len([line for line in path.read_text(encoding='utf-8').splitlines() if line.strip()])
    return {'status': 'ready', 'examples': examples, 'dataset_path': str(path)}


def main():
    """CLI entrypoint for the eval stub."""
    print('[realai] Eval stub. Add your eval suites here.')
    return evaluate_instruction_dataset()


if __name__ == '__main__':
    main()
