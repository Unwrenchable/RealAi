import os

from scripts.branch_audit import filter_relevant_files


def test_filter_relevant_files_excludes_noise_and_keeps_source_files():
    paths = [
        'realai/server/router.py',
        'apps/vscode/src/realaiClient.ts',
        'node_modules/react/index.js',
        'archive/old.py',
        'README.md',
        '.gitkeep',
        'agents/coder.agent.json',
        'package-lock.json',
        '__pycache__/module.pyc',
    ]

    filtered = filter_relevant_files(paths)

    assert 'realai/server/router.py' in filtered
    assert 'apps/vscode/src/realaiClient.ts' in filtered
    assert 'README.md' in filtered
    assert 'agents/coder.agent.json' in filtered
    assert 'node_modules/react/index.js' not in filtered
    assert 'archive/old.py' not in filtered
    assert 'package-lock.json' not in filtered
    assert '__pycache__/module.pyc' not in filtered
