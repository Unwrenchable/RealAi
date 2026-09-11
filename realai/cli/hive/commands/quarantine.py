"""Quarantine discover / catalog — feed self-improve & promote."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import click

from realai.cli.hive.format import emit_json, error, ok_line, table, truncate


def _ws(ctx) -> Path:
    ws = Path(getattr(ctx, "workspace", None) or r"C:\RealAI-clean")
    if (ws / "_quarantine").is_dir():
        return ws
    if ws.name.lower() == "realai" and (ws.parent / "_quarantine").is_dir():
        return ws.parent
    try:
        from realai.workspace import product_root

        return product_root()
    except Exception:
        return ws


@click.group("quarantine", invoke_without_command=True)
@click.pass_context
def quarantine_group(ctx):
    """Index _quarantine for unique/lost code (learn + promote)."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(quarantine_status)


@quarantine_group.command("status")
@click.pass_obj
def quarantine_status(ctx):
    ws = _ws(ctx)
    quar = ws / "_quarantine"
    cat = ws / "scan_results" / "quarantine_catalog.json"
    cand = ws / "scan_results" / "quarantine_promote_candidates.json"
    payload = {
        "quarantine_exists": quar.is_dir(),
        "quarantine": str(quar),
        "catalog_exists": cat.is_file(),
        "candidates_exists": cand.is_file(),
    }
    if cat.is_file():
        try:
            data = json.loads(cat.read_text(encoding="utf-8"))
            payload["generated_at"] = data.get("generated_at")
            payload["stats"] = data.get("stats")
            payload["count"] = data.get("count")
            payload["promote_candidates_count"] = data.get("promote_candidates_count")
        except Exception as e:
            payload["catalog_error"] = str(e)
    if ctx.as_json:
        emit_json(payload)
        return
    click.echo(f"quarantine  {quar}  exists={payload['quarantine_exists']}")
    click.echo(f"catalog     {cat}  exists={payload['catalog_exists']}")
    if payload.get("stats"):
        st = payload["stats"]
        click.echo(
            f"last scan   files={st.get('scanned_files')} entries={payload.get('count')} "
            f"promote={payload.get('promote_candidates_count')} capped={st.get('capped')}"
        )
    if not payload["catalog_exists"]:
        click.echo("Next:  realai quarantine scan")


@quarantine_group.command("scan")
@click.pass_obj
def quarantine_scan(ctx):
    """Run scripts/quarantine_catalog.py (bounded unique/keyword index)."""
    ws = _ws(ctx)
    script = ws / "scripts" / "quarantine_catalog.py"
    if not script.is_file():
        error("missing quarantine_catalog.py", detail=str(script))
        raise SystemExit(1)
    click.echo(f"running {script} …")
    rc = subprocess.call([sys.executable, str(script)], cwd=str(ws))
    if rc != 0:
        raise SystemExit(rc)
    ok_line("quarantine catalog refreshed")
    cat = ws / "scan_results" / "quarantine_catalog.json"
    if cat.is_file():
        data = json.loads(cat.read_text(encoding="utf-8"))
        if ctx.as_json:
            emit_json({"ok": True, "catalog": data.get("stats"), "promote": data.get("promote_candidates_count")})
        else:
            st = data.get("stats") or {}
            click.echo(
                f"scanned={st.get('scanned_files')} entries={data.get('count')} "
                f"promote={data.get('promote_candidates_count')}"
            )


@quarantine_group.command("list")
@click.option("--limit", default=30, show_default=True)
@click.option("--promote-only", is_flag=True, help="Only promote_review candidates")
@click.pass_obj
def quarantine_list(ctx, limit, promote_only):
    ws = _ws(ctx)
    path = (
        ws / "scan_results" / "quarantine_promote_candidates.json"
        if promote_only
        else ws / "scan_results" / "quarantine_catalog.json"
    )
    if not path.is_file():
        error("no catalog yet", hint="realai quarantine scan")
        raise SystemExit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    rows_src = data.get("candidates") if promote_only else data.get("entries")
    rows_src = rows_src or []
    if ctx.as_json:
        emit_json({"count": len(rows_src[:limit]), "entries": rows_src[:limit]})
        return
    table_rows = [
        [e.get("score"), "yes" if e.get("unique_name") else "", e.get("suggest"), truncate(e.get("rel") or "", 70)]
        for e in rows_src[:limit]
    ]
    click.echo(table(table_rows, headers=["score", "unique", "suggest", "rel"]))


@quarantine_group.command("find")
@click.argument("query")
@click.option("--limit", default=25, show_default=True)
@click.pass_obj
def quarantine_find(ctx, query, limit):
    """Substring search over last quarantine catalog."""
    ws = _ws(ctx)
    path = ws / "scan_results" / "quarantine_catalog.json"
    if not path.is_file():
        error("no catalog yet", hint="realai quarantine scan")
        raise SystemExit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    q = query.lower()
    hits = [e for e in (data.get("entries") or []) if q in (e.get("rel") or "").lower() or q in (e.get("name") or "").lower()]
    if ctx.as_json:
        emit_json({"query": query, "hits": hits[:limit]})
        return
    if not hits:
        click.echo("(no hits)")
        return
    for e in hits[:limit]:
        click.echo(f"{e.get('score'):2}  {e.get('suggest'):16}  {e.get('rel')}")
