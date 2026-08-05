"""Command-line entrypoint for structured RealAI workflows."""

import argparse
import os

try:
    import click
except ImportError:
    click = None

from realai.sdk.python.realai_client import RealAIClient


def _chat_command(prompt, model, api_url):
    client = RealAIClient(api_url=api_url)
    response = client.chat(model=model, messages=[{'role': 'user', 'content': prompt}])
    print(response['choices'][0]['message']['content'])


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

    def main(argv=None):
        """CLI entrypoint."""
        cli.main(args=argv, standalone_mode=False)
        return 0
else:
    def main(argv=None):
        """Fallback CLI entrypoint when click is unavailable."""
        parser = argparse.ArgumentParser(description='RealAI command-line interface.')
        parser.add_argument('command', choices=['chat'])
        parser.add_argument('prompt')
        parser.add_argument('--model', default='realai-1.0')
        parser.add_argument('--api-url', default=os.environ.get('REALAI_API_URL', 'http://localhost:8000'))
        args = parser.parse_args(argv)
        _chat_command(args.prompt, args.model, args.api_url)
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
