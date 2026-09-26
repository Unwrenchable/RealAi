"""Operator verify pack: short report, guarded hive, not a turn tool."""
from __future__ import annotations

import os
import socket
import threading
import time
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from abilities.console_verify_pack import (
    coverage_live_count,
    hive_health,
    run,
)
from realai.ability_catalog import RUNDOWN_ABILITIES
from realai.bot.natural_mode import (
    MAX_TOOLS_THIS_TURN,
    match_ability_ids,
    plan_natural_turn,
    post_write_smoke,
)


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b'{"status":"ok","service":"realai-v3-orchestrator"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


class TestConsoleVerifyPack(unittest.TestCase):
    def test_catalog_row_is_live_and_not_a_turn_tool(self):
        row = next(a for a in RUNDOWN_ABILITIES if a.get("id") == "console_verify_pack")
        self.assertEqual(row.get("status"), "LIVE")
        self.assertIn("abilities/console_verify_pack.py", row.get("modules") or [])
        self.assertEqual(MAX_TOOLS_THIS_TURN, 3)
        self.assertTrue(callable(post_write_smoke))
        for ask in (
            "hello there",
            "verify the write",
            "run the verify pack",
            "console verify pack",
            "check hive health on the console",
        ):
            ids = match_ability_ids(ask)
            self.assertNotIn("console_verify_pack", ids, ask)
            plans = plan_natural_turn(ask)
            self.assertLessEqual(len(plans), MAX_TOOLS_THIS_TURN, plans)
            self.assertFalse(
                any(
                    kind == "ability" and (args or {}).get("id") == "console_verify_pack"
                    for kind, args in plans
                ),
                plans,
            )

    def test_coverage_counts_memory_without_build_catalog(self):
        import realai.ability_catalog as cat

        with patch.object(cat, "build_catalog", side_effect=AssertionError("not cheap")):
            out = coverage_live_count()
        self.assertTrue(out.get("cheap"))
        self.assertGreater(int(out.get("live_count") or 0), 0)
        self.assertIn("LIVE=", out.get("line") or "")

    def test_hive_down_does_not_hang_and_does_not_retry(self):
        calls = []

        def boom(req, timeout=None):
            calls.append(timeout)
            raise urllib.error.URLError("connection refused")

        prev = os.environ.get("REALAI_API_BASE")
        os.environ["REALAI_API_BASE"] = "http://127.0.0.1:9"
        self.addCleanup(lambda: _restore_env("REALAI_API_BASE", prev))
        started = time.perf_counter()
        with patch("abilities.console_verify_pack.urllib.request.urlopen", boom):
            out = run(input="verify")
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 3.0, elapsed)
        self.assertEqual(calls, [1.5])
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("verdict"), "FAIL")
        report = out.get("report") or ""
        self.assertTrue(report.startswith("VERIFY FAIL"))
        self.assertIn("hive FAIL http://127.0.0.1:9/health", report)
        self.assertIn("orch PASS", report)
        self.assertIn("coverage PASS LIVE=", report)
        self.assertIn("console.html PASS", report)
        self.assertIn("operator directive PASS", report)
        self.assertIn("OPERATOR_MEMORY PASS", report)
        self.assertFalse(out.get("every_turn"))

    def test_blackhole_health_times_out(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]

        def hold():
            try:
                conn, _ = srv.accept()
                time.sleep(8)
                conn.close()
            except Exception:
                pass

        threading.Thread(target=hold, daemon=True).start()
        self.addCleanup(srv.close)
        prev = os.environ.get("REALAI_API_BASE")
        os.environ["REALAI_API_BASE"] = f"http://127.0.0.1:{port}"
        self.addCleanup(lambda: _restore_env("REALAI_API_BASE", prev))
        started = time.perf_counter()
        out = hive_health(timeout=0.8)
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 3.0, elapsed)
        self.assertFalse(out.get("ok"))
        self.assertIn("hive FAIL", out.get("line") or "")
        self.assertTrue(out.get("guarded"))

    def test_hive_up_is_pass(self):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), _HealthHandler)
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()

        def _stop() -> None:
            httpd.shutdown()
            httpd.server_close()

        self.addCleanup(_stop)
        prev = os.environ.get("REALAI_API_BASE")
        os.environ["REALAI_API_BASE"] = f"http://127.0.0.1:{port}"
        self.addCleanup(lambda: _restore_env("REALAI_API_BASE", prev))
        out = run(input="verify", context={"timeout": 1.5})
        report = out.get("report") or ""
        self.assertIn("hive PASS 200 ok ", report)
        self.assertTrue(report.startswith("VERIFY PASS"), report)
        self.assertTrue(out.get("ok"), report)

    def test_missing_operator_memory_fails_that_line(self):
        prev = os.environ.get("REALAI_API_BASE")
        os.environ["REALAI_API_BASE"] = "http://127.0.0.1:9"

        def boom(req, timeout=None):
            raise urllib.error.URLError("down")

        self.addCleanup(lambda: _restore_env("REALAI_API_BASE", prev))
        with patch("abilities.console_verify_pack.urllib.request.urlopen", boom), patch(
            "realai.bot.boot.operator_memory_path", return_value=None
        ):
            out = run()
        report = out.get("report") or ""
        self.assertIn("OPERATOR_MEMORY FAIL missing docs/OPERATOR_MEMORY.md", report)
        self.assertTrue(report.startswith("VERIFY FAIL"))

    def test_registry_dispatch_returns_chat_report(self):
        from realai.orchestration.v3_runtime_bridge import execute_registry_tool

        prev = os.environ.get("REALAI_API_BASE")
        os.environ["REALAI_API_BASE"] = "http://127.0.0.1:9"
        self.addCleanup(lambda: _restore_env("REALAI_API_BASE", prev))
        started = time.perf_counter()
        out = execute_registry_tool(
            "ability.console_verify_pack",
            {"input": "verify", "action": "verify"},
        )
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 3.0, elapsed)
        self.assertEqual(out.get("tool"), "ability.console_verify_pack")
        self.assertEqual(out.get("verdict"), "FAIL")
        report = out.get("report") or ""
        self.assertTrue(report.startswith("VERIFY FAIL"), report)
        self.assertIn("hive FAIL http://127.0.0.1:9/health", report)

    def test_timeout_is_capped(self):
        seen = {}

        def boom(req, timeout=None):
            seen["timeout"] = timeout
            raise urllib.error.URLError("down")

        with patch("abilities.console_verify_pack.urllib.request.urlopen", boom):
            hive_health(timeout=30)
        self.assertEqual(seen["timeout"], 30)
        with patch("abilities.console_verify_pack.urllib.request.urlopen", boom):
            out = run(context={"timeout": 30})
        self.assertEqual(out.get("timeout"), 2.5)


def _restore_env(key: str, val):
    if val is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = val


if __name__ == "__main__":
    unittest.main()
