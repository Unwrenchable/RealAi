"""Command-line entrypoint for structured RealAI workflows."""

import argparse
import json
import os

try:
    import click
except ImportError:
    click = None

from realai.sdk.python.realai_client import RealAIClient


def _make_client(api_url):
    return RealAIClient(api_url=api_url)


def _chat_command(prompt, model, api_url):
    client = _make_client(api_url)
    response = client.chat(model=model, messages=[{'role': 'user', 'content': prompt}])
    print(response['choices'][0]['message']['content'])


def _json_command(value):
    print(json.dumps(value, indent=2, sort_keys=True))


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
