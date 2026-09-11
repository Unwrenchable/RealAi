"""Non-Craft chat / ask via orchestrator."""
from __future__ import annotations

import click

from realai.cli.hive.format import emit_json, error


def _do_chat(ctx, prompt, model, agent_id, multi_mode, max_tokens):
    text = " ".join(prompt).strip() if not isinstance(prompt, str) else prompt
    if isinstance(prompt, (list, tuple)):
        text = " ".join(prompt).strip()
    try:
        resp = ctx.client.chat_completion(
            [{"role": "user", "content": text}],
            model=model,
            max_tokens=max_tokens,
            agent_id=agent_id,
            multi_agent="pipeline" if multi_mode else None,
        )
    except Exception as e:
        error("chat failed", hint="realai stack up", detail=str(e))
        raise SystemExit(1)
    if ctx.as_json:
        emit_json(resp)
        return
    content = ((resp.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    click.echo(content)


@click.command("chat")
@click.argument("prompt", nargs=-1, required=True)
@click.option("--model", default="realai-default-coder", show_default=True)
@click.option("--agent", "agent_id", default=None, help="Agent id to inject")
@click.option("--multi", "multi_mode", is_flag=True, help="Request multi-agent pipeline")
@click.option("--max-tokens", default=512, type=int)
@click.pass_obj
def chat_cmd(ctx, prompt, model, agent_id, multi_mode, max_tokens):
    """Send a prompt to the Hive orchestrator (not Craft)."""
    _do_chat(ctx, prompt, model, agent_id, multi_mode, max_tokens)


@click.command("ask")
@click.argument("prompt", nargs=-1, required=True)
@click.option("--model", default="realai-default-coder")
@click.option("--agent", "agent_id", default=None)
@click.option("--max-tokens", default=512, type=int)
@click.pass_obj
def ask_cmd(ctx, prompt, model, agent_id, max_tokens):
    """Alias for chat."""
    _do_chat(ctx, prompt, model, agent_id, False, max_tokens)
