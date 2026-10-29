"""Regression tests for Security's #210 probe (p210.py) and the fixes for HIGH 1-2, MED 3-6, LOW 7."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import pytest

from realai.orchestration import v3_runtime_bridge as b

W = b.workspace_tool
SECRET = "OUTSIDE_SECRET"


@pytest.fixture
def ws(tmp_path, monkeypatch):
    root = tmp_path / "root"
    (root / "sub" / "deep").mkdir(parents=True)
    out = tmp_path / "outside"
    out.mkdir()
    (out / "secret.txt").write_text(SECRET + "\n")
    (out / "plain.txt").write_text(SECRET + "\n")
    (root / "sub" / "a.txt").write_text("hello\n")
    (root / ".env").write_text("API_KEY=FAKE_ENV_VALUE\n")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[remote]\nurl=https://FAKE_TOKEN@github.com/x\n")
    monkeypatch.setenv("REALAI_TOOLS_WORKSPACE_ROOT", str(root))
    monkeypatch.delenv("REALAI_TOOLS_ALLOW", raising=False)
    return root, out, tmp_path


def rd(p, **k):
    return W("workspace_read", {"path": p, **k})


def _no_leak(r):
    s = json.dumps(r)
    assert SECRET not in s and "FAKE_ENV_VALUE" not in s and "FAKE_TOKEN" not in s
    return r


def _symlink(link, target, is_dir=False):
    try:
        os.symlink(target, link, target_is_directory=is_dir)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not permitted on this host")


# ---- probe block 1: path forms --------------------------------------------------
PROBE_PATHS = ["../outside/secret.txt", "sub/../../outside/secret.txt", "..\\outside\\secret.txt",
               "sub\\..\\..\\outside/secret.txt", "%2e%2e/outside/secret.txt", "..%2fsecret", "\\\\?\\C:\\x",
               "//srv/share", "C:secret", "~/x", "~", "... /x", ".. /outside/secret.txt", "..\u2024/x",
               "\uff0e\uff0e/outside/secret.txt", "sub/a.txt\x00"]


@pytest.mark.parametrize("p", PROBE_PATHS)
def test_probe_paths_refused_or_missing(ws, p):
    r = _no_leak(rd(p))
    assert r["ok"] is False


def test_probe_absolute_outside(ws):
    _, out, _ = ws
    assert _no_leak(rd(str(out / "secret.txt")))["error"] == "absolute_path_not_allowed"


@pytest.mark.parametrize("p", ["sub/a.txt", "SUB/a.txt", "sub/a.txt.", "sub/a.txt "])
def test_probe_case_and_trailing(ws, p):
    r = _no_leak(rd(p))
    if os.name == "nt":
        assert r["ok"] is True and r["content"] == "hello"
    else:
        assert r["ok"] is (p == "sub/a.txt")


# ---- HIGH 1: denylist -----------------------------------------------------------
@pytest.mark.parametrize("name", [".env", ".ENV", ".env.local", "server.pem", "x.KEY", "id_rsa", "id_ed25519.pub",
                                  "c.p12", "c.pfx", "a.keystore", ".npmrc", ".pypirc", ".netrc",
                                  "credentials.json", "Credentials", "my_secret.txt", "TopSecret.md",
                                  "x.pem.", "x.pem "])
def test_denylist_read(ws, name):
    root, _, _ = ws
    try:
        (root / name).write_text("FAKE_ENV_VALUE\n")
    except OSError:
        pass
    assert _no_leak(rd(name))["error"] == "denied_path"


@pytest.mark.parametrize("p", [".git/config", ".GIT/config", "sub/.realai/x", ".realai", "sub/secrets/x.txt",
                               "credentials/x"])
def test_denylist_any_component(ws, p):
    assert _no_leak(rd(p))["error"] == "denied_path"
    assert W("workspace_list", {"path": p})["error"] == "denied_path"
    assert W("workspace_grep", {"pattern": "x", "path": p})["error"] == "denied_path"


def test_probe_env_and_git(ws):
    assert _no_leak(rd(".env"))["error"] == "denied_path"
    assert _no_leak(rd(".git/config"))["error"] == "denied_path"


def test_list_and_grep_hide_denied(ws):
    root, _, _ = ws
    (root / "sub" / "id_rsa").write_text("FAKE_ENV_VALUE\n")
    (root / "sub" / "secret_notes.txt").write_text("FAKE_ENV_VALUE\n")
    names = {e["name"] for e in W("workspace_list", {})["entries"]}
    assert ".env" not in names and ".git" not in names
    sub = {e["name"] for e in W("workspace_list", {"path": "sub"})["entries"]}
    assert sub == {"a.txt", "deep"}
    g = W("workspace_grep", {"pattern": "FAKE"})
    assert g["ok"] and g["hits"] == []
    assert len(W("workspace_grep", {"pattern": "OUTSIDE"})["hits"]) == 0


def test_probe_regexish_pattern_is_literal(ws):
    assert W("workspace_grep", {"pattern": "(a+)+$"})["ok"] is True


# ---- HIGH 2: fail closed root ---------------------------------------------------
@pytest.mark.parametrize("v", ["", "   "])
def test_root_blank(ws, monkeypatch, v):
    monkeypatch.setenv("REALAI_TOOLS_WORKSPACE_ROOT", v)
    for t in ("workspace_list", "workspace_read", "workspace_grep"):
        assert W(t, {"path": "sub/a.txt", "pattern": "h"}) == {"ok": False, "error": "workspace_unavailable"}


def test_root_unset(ws, monkeypatch):
    monkeypatch.delenv("REALAI_TOOLS_WORKSPACE_ROOT")
    assert W("workspace_list", {}) == {"ok": False, "error": "workspace_unavailable"}


def test_no_craft_fallback():
    import inspect

    assert "craft" not in inspect.getsource(b.workspace_root)


def test_root_nonexistent(ws, monkeypatch):
    monkeypatch.setenv("REALAI_TOOLS_WORKSPACE_ROOT", str(ws[2] / "nonexistent"))
    assert W("workspace_list", {}) == {"ok": False, "error": "workspace_unavailable"}


def test_forbidden_roots(ws, monkeypatch):
    product = Path(b.__file__).resolve().parents[2]
    anchor = Path(Path.cwd().anchor)
    for r in [anchor, Path.home(), product, product.parent]:
        monkeypatch.setenv("REALAI_TOOLS_WORKSPACE_ROOT", str(r))
        assert W("workspace_list", {})["error"] == "workspace_unavailable", r


def test_symlinked_root_resolves(ws, monkeypatch):
    root, _, tmp = ws
    _symlink(tmp / "rootlink", root, True)
    monkeypatch.setenv("REALAI_TOOLS_WORKSPACE_ROOT", str(tmp / "rootlink"))
    assert rd("sub/a.txt")["content"] == "hello"


# ---- MED 3: links / TOCTOU ------------------------------------------------------
def test_probe_symlink_dir_and_file(ws):
    root, out, _ = ws
    _symlink(root / "lnk", out, True)
    _symlink(root / "sub" / "lf", out / "plain.txt")
    assert _no_leak(rd("lnk/plain.txt"))["error"] == "symlink_not_allowed"
    assert _no_leak(rd("sub/lf"))["error"] == "symlink_not_allowed"
    types = {e["name"]: e["type"] for e in W("workspace_list", {})["entries"]}
    assert types["lnk"] == "link"
    assert _no_leak(W("workspace_grep", {"pattern": "OUTSIDE"}))["hits"] == []


@pytest.mark.skipif(os.name == "nt", reason="rename/symlink race uses POSIX semantics")
def test_probe_toctou_read_race(ws):
    root, out, _ = ws
    (root / "race").mkdir()
    (root / "race" / "plain.txt").write_text("inside\n")
    stop = threading.Event()

    def flip():
        while not stop.is_set():
            try:
                os.rename(root / "race", root / "race_d")
                os.symlink(out, root / "race")
            except OSError:
                pass
            try:
                os.unlink(root / "race")
                os.rename(root / "race_d", root / "race")
            except OSError:
                pass

    th = threading.Thread(target=flip, daemon=True)
    th.start()
    leaks = sum(SECRET in json.dumps(rd("race/plain.txt")) for _ in range(1500))
    stop.set()
    th.join()
    assert leaks == 0


@pytest.mark.skipif(os.name != "nt", reason="Windows final-path check")
def test_windows_final_path_inside_root(ws):
    root, _, _ = ws
    fd = b.ws_open_read(root, ["sub", "a.txt"])
    try:
        b._nt_check_final(root, fd)
    finally:
        os.close(fd)


# ---- MED 4: grep robustness -----------------------------------------------------
@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs")
def test_probe_fifo(ws):
    root, _, _ = ws
    os.mkfifo(root / "sub" / "fifo")
    assert rd("sub/fifo")["error"] == "not_a_file"
    res = {}
    t = threading.Thread(target=lambda: res.update(g=W("workspace_grep", {"pattern": "zzz"})), daemon=True)
    t.start()
    t.join(8)
    assert not t.is_alive() and res["g"]["ok"] is True


def test_grep_depth_cap(ws, monkeypatch):
    root, _, _ = ws
    monkeypatch.setattr(b, "WS_GREP_MAX_DEPTH", 2)
    d = root
    for i in range(5):
        d = d / f"d{i}"
        d.mkdir()
        (d / "f.txt").write_text("needle\n")
    paths = {h["path"] for h in W("workspace_grep", {"pattern": "needle"})["hits"]}
    assert paths == {"d0/f.txt", "d0/d1/f.txt"}  # 2 levels below the grep base


def test_grep_deadline(ws, monkeypatch):
    root, _, _ = ws
    monkeypatch.setattr(b, "WS_GREP_DEADLINE_S", -1.0)
    r = W("workspace_grep", {"pattern": "hello"})
    assert r["ok"] and r["truncated"] is True


def test_grep_byte_budget(ws, monkeypatch):
    root, _, _ = ws
    monkeypatch.setattr(b, "WS_MAX_GREP_TOTAL_BYTES", 10)
    for i in range(5):
        (root / f"g{i}.txt").write_text("needle " * 5)
    r = W("workspace_grep", {"pattern": "needle"})
    assert r["truncated"] is True and len(r["hits"]) < 5


# ---- MED 5: hard links ----------------------------------------------------------
def _hardlink(src, dst):
    try:
        os.link(src, dst)
    except (OSError, NotImplementedError):
        pytest.skip("hard links not permitted on this host")


def test_probe_hardlink_read(ws):
    root, out, _ = ws
    _hardlink(out / "plain.txt", root / "hard.txt")
    assert _no_leak(rd("hard.txt"))["error"] == "hardlink_not_allowed"
    assert _no_leak(W("workspace_grep", {"pattern": "OUTSIDE"}))["hits"] == []


def test_probe_hardlink_write(ws, monkeypatch):
    root, out, _ = ws
    monkeypatch.setenv("REALAI_TOOLS_ALLOW", "workspace_write")
    _hardlink(out / "plain.txt", root / "hard.txt")
    r = W("workspace_write", {"path": "hard.txt", "content": "PWNED\n"})
    assert r["error"] == "hardlink_not_allowed"
    assert (out / "plain.txt").read_text() == SECRET + "\n"


def test_probe_write_without_allow(ws):
    assert W("workspace_write", {"path": "n.txt", "content": "x"})["error"] == "write_not_allowed"


def test_probe_write_symlink(ws, monkeypatch):
    root, out, _ = ws
    monkeypatch.setenv("REALAI_TOOLS_ALLOW", "workspace_write")
    _symlink(root / "sub" / "lf", out / "plain.txt")
    assert W("workspace_write", {"path": "sub/lf", "content": "pwn"})["error"] == "symlink_not_allowed"
    assert (out / "plain.txt").read_text() == SECRET + "\n"


def test_write_denylist(ws, monkeypatch):
    root, _, _ = ws
    monkeypatch.setenv("REALAI_TOOLS_ALLOW", "workspace_write")
    for p in [".env", ".git/hooks/pre-commit", "deploy.pem", "sub/credentials.yml"]:
        assert W("workspace_write", {"path": p, "content": "x"})["error"] == "denied_path", p
    assert (root / ".env").read_text().startswith("API_KEY")


# ---- LOW 7: caps + binary -------------------------------------------------------
def test_probe_huge_line(ws):
    root, _, _ = ws
    (root / "big.txt").write_text("x" * 900000)
    r = rd("big.txt")
    assert len(r["content"]) <= b.WS_MAX_LINE and r["truncated"] is True


def test_content_cap(ws):
    root, _, _ = ws
    (root / "wide.txt").write_text(("y" * 3000 + "\n") * 150)
    r = rd("wide.txt", limit=200)
    assert len(r["content"].encode()) <= b.WS_MAX_CONTENT and r["truncated"] is True


def test_probe_binary(ws):
    root, _, _ = ws
    (root / "bin.dat").write_bytes(b"\x00" + os.urandom(4999))
    assert rd("bin.dat")["error"] == "binary_not_allowed"


def test_probe_limit_huge(ws):
    assert len(rd("sub/a.txt", limit=10**9)["lines"]) == 1


def test_write_cap_is_256k(ws, monkeypatch):
    monkeypatch.setenv("REALAI_TOOLS_ALLOW", "workspace_write")
    assert b.WS_MAX_WRITE_BYTES == 256 * 1024
    assert W("workspace_write", {"path": "w.txt", "content": "x" * (256 * 1024 + 1)})["error"] == "content_too_large"
    assert W("workspace_write", {"path": "w.txt", "content": "x" * (256 * 1024)})["ok"] is True


# ---- errors never echo server paths ---------------------------------------------
def test_probe_error_path_leak(ws):
    _, _, tmp = ws
    s = json.dumps([rd("nope/x"), W("workspace_list", {"path": "nope"})])
    assert str(tmp) not in s and str(tmp).replace("\\", "\\\\") not in s


# ---- MED 6: approval gate edits use the same controls ----------------------------
@pytest.fixture
def gate(ws, monkeypatch):
    root, _, tmp = ws
    monkeypatch.setenv("REALAI_WORKSPACE", str(root))
    monkeypatch.setenv("REALAI_APPROVALS_STORE", str(tmp / "store" / ".approvals.json"))
    monkeypatch.setenv("APPROVALS_STORE", str(tmp / "store" / ".approvals.json"))
    monkeypatch.delenv("REALAI_APPROVALS_AUDIT", raising=False)
    from realai.core import approval_gate as g

    return g, root, tmp


def test_gate_checks_allow_before_queueing(gate):
    g, root, tmp = gate
    r = g.request("write_file", {"file_path": "n.txt", "content": "x"})
    assert r["status"] == "refused" and r["error"] == "write_not_allowed"
    store = tmp / "store" / ".approvals.json"
    assert not store.exists() or json.loads(store.read_text())["items"] == []


def test_gate_execute_goes_through_ws_write(gate, monkeypatch):
    g, root, tmp = gate
    monkeypatch.setenv("REALAI_TOOLS_ALLOW", "workspace_write")
    rid = g.request("write_file", {"file_path": "sub/n.txt", "content": "hi"})["approval_id"]
    g.set_status(rid, "approved", by="t")
    calls = []
    real = b._ws_write
    monkeypatch.setattr(b, "_ws_write", lambda root_, a: calls.append(a) or real(root_, a))
    assert g.execute(rid)["ok"] is True and calls and (root / "sub" / "n.txt").read_text() == "hi"


def test_gate_allow_removed_after_approval(gate, monkeypatch):
    g, root, _ = gate
    monkeypatch.setenv("REALAI_TOOLS_ALLOW", "workspace_write")
    rid = g.request("write_file", {"file_path": "late.txt", "content": "x"})["approval_id"]
    g.set_status(rid, "approved", by="t")
    monkeypatch.delenv("REALAI_TOOLS_ALLOW")
    assert g.execute(rid)["ok"] is False and not (root / "late.txt").exists()


def test_gate_refuses_denied_and_hardlink(gate, monkeypatch):
    g, root, tmp = gate
    monkeypatch.setenv("REALAI_TOOLS_ALLOW", "workspace_write")
    for p in [".env", "x/id_rsa", "secret.txt", "../outside/plain.txt"]:
        assert g.request("write_file", {"file_path": p, "content": "x"})["status"] == "refused", p
    _hardlink(tmp / "outside" / "plain.txt", root / "hl.txt")
    assert g.request("search_replace", {"file_path": "hl.txt", "old_string": "OUT", "new_string": "X"})["status"] == "refused"
    assert (tmp / "outside" / "plain.txt").read_text() == SECRET + "\n"


def test_gate_fails_closed_without_root(gate, monkeypatch):
    g, _, _ = gate
    monkeypatch.setenv("REALAI_TOOLS_ALLOW", "workspace_write")
    monkeypatch.delenv("REALAI_TOOLS_WORKSPACE_ROOT")
    r = g.request("write_file", {"file_path": "n.txt", "content": "x"})
    assert r["status"] == "refused" and r["error"] == "workspace_unavailable"


def test_bridge_search_replace_confined(ws, monkeypatch):
    root, _, _ = ws
    assert b.execute_registry_tool("search_replace", {"path": "sub/a.txt", "old_string": "hello", "new_string": "bye"})["error"] == "write_not_allowed"
    monkeypatch.setenv("REALAI_TOOLS_ALLOW", "workspace_write")
    assert b.execute_registry_tool("search_replace", {"path": ".env", "old_string": "API", "new_string": "X"})["error"] == "denied_path"
    out = b.execute_registry_tool("search_replace", {"path": "sub/a.txt", "old_string": "hello", "new_string": "bye"})
    assert out["ok"] is True and (root / "sub" / "a.txt").read_text() == "bye\n"
