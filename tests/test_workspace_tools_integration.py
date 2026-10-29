"""B3 piece 1: workspace tools over POST /v1/tools/execute (integration + security)."""
from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from realai.orchestration import v3_runtime_bridge as bridge
from realai.orchestration import tool_auth

TOKEN = "ws-test-token-123"


@pytest.fixture
def ws(tmp_path, monkeypatch):
    root = tmp_path / "ws"
    root.mkdir()
    (root / "hello.txt").write_text("line one\nneedle here\nline three\n", encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub" / "a.py").write_text("x = 1\n# needle\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("TOP SECRET needle", encoding="utf-8")
    monkeypatch.setenv("REALAI_TOOLS_WORKSPACE_ROOT", str(root))
    monkeypatch.delenv("REALAI_TOOLS_ALLOW", raising=False)
    return root, outside


def _find(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _find(v, key)
            if r is not None:
                return r
    return None


@pytest.fixture
def server(ws, monkeypatch):
    from realai.orchestration import v3_orchestrator as orch

    monkeypatch.setenv("REALAI_TOOLS_AUTH", "1")
    monkeypatch.setenv("REALAI_TOOLS_TOKEN", TOKEN)
    monkeypatch.setenv("REALAI_TOOLS_RATE", "1000")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), orch.Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield "http://127.0.0.1:%d" % httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


def _post(base, body, token=TOKEN):
    req = urllib.request.Request(base + "/v1/tools/execute", data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


# ---- integration over HTTP -------------------------------------------------

def test_http_read_list_grep(server, ws):
    st, body = _post(server, {"name": "workspace_read", "arguments": {"path": "hello.txt"}})
    assert st == 200, body
    assert "needle here" in _find(body, "lines")
    st, body = _post(server, {"name": "workspace_list", "arguments": {"path": "."}})
    assert st == 200
    names = {e["name"] for e in _find(body, "entries")}
    assert {"hello.txt", "sub"} <= names
    st, body = _post(server, {"name": "workspace_grep", "arguments": {"pattern": "needle"}})
    assert st == 200
    paths = {h["path"] for h in _find(body, "hits")}
    assert paths == {"hello.txt", "sub/a.py"}


def test_http_requires_token(server):
    st, _ = _post(server, {"name": "workspace_read", "arguments": {"path": "hello.txt"}}, token=None)
    assert st == 401
    st, _ = _post(server, {"name": "workspace_read", "arguments": {"path": "hello.txt"}}, token="wrong")
    assert st == 401


def test_http_write_not_in_default_allowlist(server, ws):
    st, _ = _post(server, {"name": "workspace_write", "arguments": {"path": "x.txt", "content": "hi"}})
    assert st == 403
    assert not (ws[0] / "x.txt").exists()


def test_http_traversal_blocked(server, ws):
    st, body = _post(server, {"name": "workspace_read", "arguments": {"path": "../outside/secret.txt"}})
    assert "TOP SECRET" not in json.dumps(body)
    assert _find(body, "error") == "path_traversal_not_allowed"


def test_default_allowlist_has_read_tools_only():
    allow = tool_auth.default_allowlist()
    for n in bridge.WS_READ_TOOLS:
        assert n in allow
    assert "workspace_write" not in allow


# ---- security: direct ------------------------------------------------------

@pytest.mark.parametrize("p", ["..", "../outside/secret.txt", "sub/../../outside/secret.txt",
                               "sub\\..\\..\\outside\\secret.txt", "./../outside"])
def test_traversal(ws, p):
    r = bridge.workspace_tool("workspace_read", {"path": p})
    assert r["ok"] is False and r["error"] == "path_traversal_not_allowed"


def test_absolute_paths(ws):
    root, outside = ws
    for p in [str(outside / "secret.txt"), str(root / "hello.txt"), "/etc/passwd", "\\Windows\\win.ini",
              "C:\\Windows\\win.ini", "C:secret.txt", "c:/x"]:
        r = bridge.workspace_tool("workspace_read", {"path": p})
        assert r["ok"] is False, p
        assert r["error"] in ("absolute_path_not_allowed", "unc_path_not_allowed"), (p, r)


@pytest.mark.parametrize("p", ["\\\\server\\share\\x.txt", "//server/share/x.txt",
                               "\\\\?\\C:\\Windows\\win.ini", "\\\\.\\pipe\\x"])
def test_unc_paths(ws, p):
    r = bridge.workspace_tool("workspace_read", {"path": p})
    assert r["ok"] is False and r["error"] == "unc_path_not_allowed"


def test_nul_and_type(ws):
    assert bridge.workspace_tool("workspace_read", {"path": "hello.txt\x00"})["error"] == "bad_path"
    assert bridge.workspace_tool("workspace_read", {"path": ["hello.txt"]})["error"] == "bad_path_type"
    assert bridge.workspace_tool("workspace_read", {"path": "a" * 5000})["error"] == "bad_path"


def _symlink(link, target, is_dir):
    try:
        os.symlink(target, link, target_is_directory=is_dir)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not permitted on this host")


def test_symlink_file_escape(ws):
    root, outside = ws
    _symlink(root / "leak.txt", outside / "secret.txt", False)
    r = bridge.workspace_tool("workspace_read", {"path": "leak.txt"})
    assert r == {"ok": False, "error": "symlink_not_allowed"}


def test_symlink_dir_escape(ws):
    root, outside = ws
    _symlink(root / "out", outside, True)
    assert bridge.workspace_tool("workspace_read", {"path": "out/secret.txt"})["error"] == "symlink_not_allowed"
    assert bridge.workspace_tool("workspace_list", {"path": "out"})["error"] == "symlink_not_allowed"
    g = bridge.workspace_tool("workspace_grep", {"pattern": "SECRET"})
    assert g["ok"] and g["hits"] == []


def test_symlink_inside_root_also_refused(ws):
    root, _ = ws
    _symlink(root / "alias.txt", root / "hello.txt", False)
    assert bridge.workspace_tool("workspace_read", {"path": "alias.txt"})["error"] == "symlink_not_allowed"


def test_junction_escape_windows(ws):
    if os.name != "nt":
        pytest.skip("junctions are Windows-only")
    import subprocess

    root, outside = ws
    rc = subprocess.run(["cmd", "/c", "mklink", "/J", str(root / "jn"), str(outside)], capture_output=True)
    if rc.returncode != 0:
        pytest.skip("mklink /J failed")
    assert bridge.workspace_tool("workspace_read", {"path": "jn/secret.txt"})["error"] == "symlink_not_allowed"
    g = bridge.workspace_tool("workspace_grep", {"pattern": "SECRET"})
    assert g["hits"] == []


def test_oversize_read(ws, monkeypatch):
    root, _ = ws
    monkeypatch.setattr(bridge, "WS_MAX_READ_BYTES", 100)
    (root / "big.txt").write_bytes(b"a" * 101)
    r = bridge.workspace_tool("workspace_read", {"path": "big.txt"})
    assert r["ok"] is False and r["error"] == "file_too_large"


def test_line_limit_clamped(ws):
    root, _ = ws
    (root / "many.txt").write_text("\n".join(str(i) for i in range(1000)), encoding="utf-8")
    r = bridge.workspace_tool("workspace_read", {"path": "many.txt", "limit": 10_000})
    assert len(r["lines"]) == bridge.WS_MAX_LINES
    assert bridge.workspace_tool("workspace_read", {"path": "many.txt", "limit": "x"})["error"] == "bad_number"


def test_list_and_grep_caps(ws, monkeypatch):
    root, _ = ws
    monkeypatch.setattr(bridge, "WS_MAX_LIST", 3)
    monkeypatch.setattr(bridge, "WS_MAX_GREP_HITS", 2)
    for i in range(10):
        (root / f"f{i}.txt").write_text("needle\n", encoding="utf-8")
    r = bridge.workspace_tool("workspace_list", {})
    assert len(r["entries"]) == 3 and r["truncated"] is True
    g = bridge.workspace_tool("workspace_grep", {"pattern": "needle"})
    assert len(g["hits"]) == 2 and g["truncated"] is True
    assert bridge.workspace_tool("workspace_grep", {"pattern": "x" * 500})["error"] == "bad_pattern"


def test_grep_oversize_file_skipped(ws, monkeypatch):
    root, _ = ws
    monkeypatch.setattr(bridge, "WS_MAX_GREP_FILE_BYTES", 50)
    (root / "huge.txt").write_text("needle" + "z" * 100, encoding="utf-8")
    g = bridge.workspace_tool("workspace_grep", {"pattern": "needle", "glob": "huge.txt"})
    assert g["hits"] == []


def test_write_off_by_default(ws):
    root, _ = ws
    r = bridge.workspace_tool("workspace_write", {"path": "new.txt", "content": "hi"})
    assert r["ok"] is False and r["error"] == "write_not_allowed"
    assert not (root / "new.txt").exists()


def test_write_when_allowed_and_confined(ws, monkeypatch):
    root, outside = ws
    monkeypatch.setenv("REALAI_TOOLS_ALLOW", "workspace_read,workspace_write")
    r = bridge.workspace_tool("workspace_write", {"path": "d/new.txt", "content": "hi"})
    assert r["ok"] is True and (root / "d" / "new.txt").read_text() == "hi"
    r = bridge.workspace_tool("workspace_write", {"path": "d/new.txt", "content": "!", "mode": "append"})
    assert (root / "d" / "new.txt").read_text() == "hi!"
    assert bridge.workspace_tool("workspace_write", {"path": "../outside/x.txt", "content": "x"})["ok"] is False
    assert bridge.workspace_tool("workspace_write", {"path": str(outside / "x.txt"), "content": "x"})["ok"] is False
    assert not (outside / "x.txt").exists()
    assert bridge.workspace_tool("workspace_write", {"path": "y.txt", "content": "x", "mode": "chmod"})["error"] == "bad_mode"


def test_write_oversize(ws, monkeypatch):
    monkeypatch.setenv("REALAI_TOOLS_ALLOW", "workspace_write")
    monkeypatch.setattr(bridge, "WS_MAX_WRITE_BYTES", 10)
    r = bridge.workspace_tool("workspace_write", {"path": "w.txt", "content": "x" * 11})
    assert r["error"] == "content_too_large"


def test_write_through_symlink_refused(ws, monkeypatch):
    root, outside = ws
    monkeypatch.setenv("REALAI_TOOLS_ALLOW", "workspace_write")
    _symlink(root / "out", outside, True)
    r = bridge.workspace_tool("workspace_write", {"path": "out/pwn.txt", "content": "x"})
    assert r["error"] == "symlink_not_allowed"
    assert not (outside / "pwn.txt").exists()


def test_errors_do_not_leak_paths(ws):
    root, outside = ws
    for p in ["../outside/secret.txt", str(outside / "secret.txt"), "missing.txt"]:
        out = json.dumps(bridge.workspace_tool("workspace_read", {"path": p}))
        assert str(root) not in out.replace("\\\\", "\\")
        assert "TOP SECRET" not in out


def test_unknown_tool(ws):
    assert bridge.workspace_tool("workspace_rm", {})["error"] == "unknown_workspace_tool:workspace_rm"


def test_catalog_flipped():
    from realai.ability_catalog import RUNDOWN_ABILITIES

    row = {r["id"]: r for r in RUNDOWN_ABILITIES}["workspace_info"]
    assert row["status"] == "LIVE"
