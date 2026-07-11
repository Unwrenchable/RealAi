"""Command-line entrypoint for structured RealAI workflows."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import click
except ImportError:
    click = None

from realai.sdk.python.realai_client import RealAIClient
from realai.training.extract_from_agent_tools import extract_agent_tool_data
from realai.training.finetune import build_finetune_plan


def _make_client(api_url):
    return RealAIClient(api_url=api_url)


def _chat_command(prompt, model, api_url):
    client = _make_client(api_url)
    response = client.chat(model=model, messages=[{'role': 'user', 'content': prompt}])
    choices = response.get('choices') or []
    if choices and isinstance(choices[0], dict):
        message_obj = choices[0].get('message')
        if isinstance(message_obj, dict):
            content = message_obj.get('content', '')
        else:
            content = ''
    else:
        content = ''
    print(content)


def _json_command(value):
    print(json.dumps(value, indent=2, sort_keys=True))


def _git_info(repo_path: Path, compare_branch: str = 'main'):
    repo_path = repo_path.resolve()
    branch = 'unknown'
    diff_against_default = 'unknown'
    try:
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=str(repo_path),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        pass
    try:
        diff_against_default = subprocess.check_output(
            ['git', 'rev-list', '--left-right', '--count', f'{compare_branch}...HEAD'],
            cwd=str(repo_path),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        diff_against_default = '0\t0'
    return {
        'repo_path': str(repo_path),
        'branch': branch,
        'diff_against_default': diff_against_default,
    }


def _run_tests(repo_path: Path):
    proc = subprocess.run(
        [sys.executable, '-m', 'pytest', '-q'],
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        'returncode': proc.returncode,
        'stdout': proc.stdout,
        'stderr': proc.stderr,
    }


if click is not None:
    @click.group()
    def cli():
        """RealAI CLI."""

    @cli.command()
    @click.argument('prompt')
    @click.option('--model', default='realai-1.0')
    @click.option('--api-url', envvar='REALAI_API_URL', default='http://localhost:8000')
    def chat(prompt, model, api_url):
        """Send a prompt to the RealAI server."""
        _chat_command(prompt, model, api_url)

    @cli.command('health')
    @click.option('--api-url', envvar='REALAI_API_URL', default='http://localhost:8000')
    def health(api_url):
        """Show server health."""
        _json_command(_make_client(api_url).health())

    @cli.command('models')
    @click.option('--api-url', envvar='REALAI_API_URL', default='http://localhost:8000')
    def models(api_url):
        """List server models."""
        _json_command(_make_client(api_url).models())

    @cli.command('providers')
    @click.option('--api-url', envvar='REALAI_API_URL', default='http://localhost:8000')
    def providers(api_url):
        """List configured providers."""
        _json_command(_make_client(api_url).providers())

    @cli.command('tasks')
    @click.option('--api-url', envvar='REALAI_API_URL', default='http://localhost:8000')
    def tasks(api_url):
        """List persisted tasks."""
        _json_command(_make_client(api_url).list_tasks())

    @cli.command('extract-data')
    @click.option('--input-root', default=None)
    @click.option('--output-root', default=None)
    def extract_data(input_root, output_root):
        """Extract training data from agent tools into JSONL."""
        _json_command(extract_agent_tool_data(input_root=input_root, output_root=output_root))

    @cli.command('finetune-plan')
    @click.option('--data-dir', default=None)
    def finetune_plan(data_dir):
        """Build a fine-tune plan from prepared datasets."""
        _json_command(build_finetune_plan(data_dir=data_dir))

    @cli.command('benchmark')
    def benchmark():
        """Run lightweight benchmark stub."""
        _json_command({'status': 'ready', 'benchmark': 'stub'})

    @cli.command('repo-loop')
    @click.argument('repo_path')
    @click.option('--report-path', default=None)
    @click.option('--compare-branch', default='main')
    def repo_loop(repo_path, report_path, compare_branch):
        """Run tests and emit a JSON report for a target repository."""
        repo = Path(repo_path).resolve()
        payload = {
            'ok': True,
            'repo': _git_info(repo, compare_branch=compare_branch),
            'tests': _run_tests(repo),
        }
        if report_path:
            Path(report_path).write_text(json.dumps(payload, indent=2), encoding='utf-8')
        _json_command(payload)

    @cli.command('doctor')
    @click.option('--repo-path', default='.')
    @click.option('--compare-branch', default='main')
    def doctor(repo_path, compare_branch):
        """Validate local CLI and repository health."""
        repo = Path(repo_path).resolve()
        checks = []
        try:
            output = subprocess.check_output(
                [sys.executable, '-m', 'realai.cli.realai_cli', '--help'],
                text=True,
                stderr=subprocess.STDOUT,
            )
            checks.append({'name': 'realai_cli_help', 'ok': 'Usage:' in output})
        except Exception as exc:
            checks.append({'name': 'realai_cli_help', 'ok': False, 'error': str(exc)})

        payload = {
            'ok': all(check.get('ok', False) for check in checks),
            'repo': _git_info(repo, compare_branch=compare_branch),
            'checks': checks,
        }
        _json_command(payload)

    def main(argv=None):
        """CLI entrypoint."""
        cli.main(args=argv, standalone_mode=False)
        return 0
else:
    def main(argv=None):
        """Fallback CLI entrypoint when click is unavailable."""
        parser = argparse.ArgumentParser(description='RealAI command-line interface.')
        parser.add_argument('command', choices=['chat', 'health', 'models', 'providers', 'tasks'])
        parser.add_argument('prompt', nargs='?')
        parser.add_argument('--model', default='realai-1.0')
        parser.add_argument('--api-url', default=os.environ.get('REALAI_API_URL', 'http://localhost:8000'))
        args = parser.parse_args(argv)
        if args.command == 'chat':
            _chat_command(args.prompt or '', args.model, args.api_url)
        elif args.command == 'health':
            _json_command(_make_client(args.api_url).health())
        elif args.command == 'models':
            _json_command(_make_client(args.api_url).models())
        elif args.command == 'providers':
            _json_command(_make_client(args.api_url).providers())
        elif args.command == 'tasks':
            _json_command(_make_client(args.api_url).list_tasks())
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
