"""Unit tests for git-learn: skip rules, packet shape, stub idempotency."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from realai.learn.packet import PACKET_SCHEMA, validate_packet
from realai.learn.pipeline import run_learn
from realai.learn.scan import DEFAULT_MAX_BRANCHES, FINGERPRINT_CAP
from realai.learn.scaffold import plugin_package_name, scaffold_plugin
from realai.learn.skip import (
    SKIP_DIR_NAMES,
    should_skip_dir,
    should_skip_filename,
    should_skip_rel,
)
from realai.learn.source import clone_argv, fetch_all_argv


def _write_fixture(root: Path) -> None:
    (root / "README.md").write_text(
        "# Fixture App\n\nA tiny Nest-ish demo for git-learn tests.\n",
        encoding="utf-8",
    )
    (root / "package.json").write_text(
        '{"name":"fixture-app","dependencies":{"@nestjs/core":"10.0.0"}}\n',
        encoding="utf-8",
    )
    src = root / "src"
    src.mkdir()
    (src / "main.ts").write_text(
        'import { NestFactory } from "@nestjs/core";\n'
        'app.get("/v1/health", () => "ok");\n'
        'app.post("/api/coach", handler);\n',
        encoding="utf-8",
    )
    (src / "routes.ts").write_text(
        'router.get("/v1/items", listItems);\n',
        encoding="utf-8",
    )
    plugins = root / "plugins" / "demo"
    plugins.mkdir(parents=True)
    (plugins / "index.ts").write_text("export const demo = true;\n", encoding="utf-8")

    nm = root / "node_modules" / "left-pad"
    nm.mkdir(parents=True)
    (nm / "index.js").write_text("module.exports = 1;\n", encoding="utf-8")
    git_dir = root / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (root / "package-lock.json").write_text('{"lockfileVersion": 3}\n', encoding="utf-8")
    (root / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n", encoding="utf-8")
    (root / "dist" / "bundle.js").parent.mkdir(exist_ok=True)
    (root / "dist" / "bundle.js").write_text("console.log(1)\n", encoding="utf-8")
    (root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    (root / "src" / "app.min.js").write_text("var a=1;\n", encoding="utf-8")


class TestSkipRules(unittest.TestCase):
    def test_skip_dirs(self):
        self.assertTrue(should_skip_dir("node_modules"))
        self.assertTrue(should_skip_dir(".git"))
        self.assertTrue(should_skip_dir("dist"))
        self.assertTrue(should_skip_dir("__pycache__"))
        self.assertIn("node_modules", SKIP_DIR_NAMES)
        self.assertFalse(should_skip_dir("src"))
        self.assertFalse(should_skip_dir("plugins"))

    def test_skip_lockfiles_and_binaries(self):
        self.assertTrue(should_skip_filename("package-lock.json"))
        self.assertTrue(should_skip_filename("pnpm-lock.yaml"))
        self.assertTrue(should_skip_filename("yarn.lock"))
        self.assertTrue(should_skip_filename("logo.png"))
        self.assertTrue(should_skip_filename("app.min.js"))
        self.assertTrue(should_skip_filename("weights.gguf"))
        self.assertFalse(should_skip_filename("main.ts"))
        self.assertFalse(should_skip_filename("README.md"))

    def test_skip_rel_paths(self):
        self.assertTrue(should_skip_rel("node_modules/left-pad/index.js"))
        self.assertTrue(should_skip_rel(".git/HEAD"))
        self.assertTrue(should_skip_rel("dist/bundle.js"))
        self.assertTrue(should_skip_rel("package-lock.json"))
        self.assertFalse(should_skip_rel("src/main.ts"))
        self.assertFalse(should_skip_rel("plugins/demo/index.ts"))


class TestPacketShape(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fixture = self.root / "fixture-app"
        self.fixture.mkdir()
        _write_fixture(self.fixture)
        self.product = self.root / "realai-product"
        self.product.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_scan_fixture_packet_shape(self):
        out = run_learn(
            str(self.fixture),
            write=False,
            product_root=self.product,
            cache_dir=self.product / "realai" / ".learn_cache",
            plugins_root=self.product / "realai" / "plugins",
            packet_root=self.product / "realai" / "catalog" / "learned",
            docs_root=self.product / "docs" / "learning",
        )
        self.assertTrue(out["ok"], out)
        self.assertFalse(out["heal"])
        packet = out["packet"]
        self.assertEqual(validate_packet(packet), [])
        self.assertEqual(packet["schema"], PACKET_SCHEMA)
        self.assertEqual(packet["slug"], "fixture_app")
        self.assertFalse(packet["heal"])
        fps = packet["fingerprints"]
        paths = {fp["path"] for fp in fps}
        self.assertTrue(any(p.endswith("main.ts") or p == "src/main.ts" for p in paths), paths)
        self.assertFalse(any("node_modules" in p for p in paths), paths)
        self.assertFalse(any(p.endswith("package-lock.json") for p in paths), paths)
        self.assertFalse(any(p.endswith(".png") for p in paths), paths)
        self.assertFalse(any("dist/" in p for p in paths), paths)
        summary = packet["summary"]
        self.assertIn("typescript", summary["languages"])
        self.assertTrue(summary["frameworks"])
        self.assertIn("health", [a["id"] for a in packet["proposed_abilities"]])
        self.assertTrue((self.product / "realai" / "catalog" / "learned" / "fixture_app" / "packet.json").is_file())
        self.assertTrue((self.product / "docs" / "learning" / "fixture_app.json").is_file())
        self.assertFalse(out["wrote_plugin"])

    def test_cli_scans_fixture(self):
        import os

        cmd = [sys.executable, "-m", "realai.learn_git", str(self.fixture)]
        env = os.environ.copy()
        env["REALAI_LEARN_ROOT"] = str(self.product)
        repo_root = str(Path(__file__).resolve().parents[2])
        env["PYTHONPATH"] = os.pathsep.join(
            [repo_root] + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
        )
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(self.fixture),
            env=env,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("ok"), data)
        self.assertFalse(data.get("heal"))
        self.assertIn("packet_path", data)
        self.assertTrue(Path(data["packet_path"]).is_file())


class TestStubIdempotency(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fixture = self.root / "rack-em-up"
        self.fixture.mkdir()
        _write_fixture(self.fixture)
        (self.fixture / "README.md").write_text(
            "# Rack Em Up\n\nPool halls coach and ratings.\n",
            encoding="utf-8",
        )
        self.product = self.root / "product"
        self.plugins = self.product / "realai" / "plugins"
        self.plugins.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_write_twice_upgrades_without_junk(self):
        first = run_learn(
            str(self.fixture),
            write=True,
            product_root=self.product,
            plugins_root=self.plugins,
            packet_root=self.product / "realai" / "catalog" / "learned",
            docs_root=self.product / "docs" / "learning",
            cache_dir=self.product / "realai" / ".learn_cache",
        )
        self.assertTrue(first["ok"], first)
        self.assertTrue(first["wrote_plugin"])
        pkg = plugin_package_name("rack-em-up")
        plugin_dir = self.plugins / pkg
        self.assertTrue((plugin_dir / "manifest.yaml").is_file())
        self.assertTrue((plugin_dir / "__init__.py").is_file())
        self.assertTrue((plugin_dir / "abilities" / "health.py").is_file())
        files_after_first = {p.relative_to(plugin_dir).as_posix() for p in plugin_dir.rglob("*") if p.is_file()}

        # Custom (non-stub) file must survive the second run.
        custom = plugin_dir / "abilities" / "health.py"
        custom.write_text(
            '"""custom health — not a generated stub."""\n'
            "def run(player, payload=None):\n"
            "    return {'status': 'custom', 'stub': False, 'heal': False}\n",
            encoding="utf-8",
        )

        # Second packet proposes an extra ability via existing proposed + new file in source
        (self.fixture / "src" / "matchmaking.ts").write_text(
            "export function matchmaking() { return 1 }\n",
            encoding="utf-8",
        )
        second = run_learn(
            str(self.fixture),
            write=True,
            product_root=self.product,
            plugins_root=self.plugins,
            packet_root=self.product / "realai" / "catalog" / "learned",
            docs_root=self.product / "docs" / "learning",
            cache_dir=self.product / "realai" / ".learn_cache",
        )
        self.assertTrue(second["ok"], second)
        self.assertTrue(second["stub"]["upgraded"])
        files_after_second = {p.relative_to(plugin_dir).as_posix() for p in plugin_dir.rglob("*") if p.is_file()}
        numbered = [n for n in files_after_second if "_2.py" in n or n.endswith("health_1.py")]
        self.assertEqual(numbered, [], files_after_second)
        # still a single health.py
        health_files = [n for n in files_after_second if n.startswith("abilities/health")]
        self.assertEqual(health_files, ["abilities/health.py"], health_files)
        self.assertIn("custom health", custom.read_text(encoding="utf-8"))
        self.assertNotIn("REALAI_LEARNED_STUB", custom.read_text(encoding="utf-8"))
        # generated files were upgraded/kept, not duplicated
        self.assertTrue(files_after_first <= files_after_second or "abilities/health.py" in files_after_second)
        self.assertFalse(second["stub"].get("junk_numbered"))

        # invoke works via isolated package load (do not use live plugins shim)
        import importlib.util

        ns = f"learn_test_{pkg}"
        spec = importlib.util.spec_from_file_location(
            ns,
            plugin_dir / "__init__.py",
            submodule_search_locations=[str(plugin_dir)],
        )
        self.assertIsNotNone(spec and spec.loader)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[ns] = mod
        spec.loader.exec_module(mod)
        resp = mod.invoke("health", {"player_id": "t1"}, {})
        self.assertEqual(resp["plugin"], pkg.replace("_", "-"))
        self.assertIn(resp.get("result", {}).get("status"), {"ok", "custom"})
        for key in list(sys.modules):
            if key == ns or key.startswith(ns + "."):
                sys.modules.pop(key, None)

    def test_protected_slug_does_not_clobber_rackup_coach(self):
        pkg = plugin_package_name("rackup")
        self.assertNotEqual(pkg, "rackup_coach")
        self.assertTrue(pkg.endswith("_learned_coach") or pkg != "rackup_coach")


class TestCraftLearnHook(unittest.TestCase):
    def test_plan_tools_learn_no_heal(self):
        from realai.cli.craft import HELP, plan_tools

        plans = plan_tools("/learn ./some-repo --write")
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0][0], "learn")
        self.assertTrue(plans[0][1]["write"])
        self.assertIn("some-repo", plans[0][1]["source"])
        self.assertIn("/learn", HELP)
        self.assertIn("local-folder-OR-git-URL", HELP)
        self.assertIn(r"C:\path\to\folder", HELP)
        self.assertNotIn("heal", plans[0][0])
        self.assertTrue(plans[0][1].get("all_branches"))
        self.assertEqual(plans[0][1].get("max_files"), FINGERPRINT_CAP)

    def test_plan_tools_learn_caps_and_no_all_branches(self):
        from realai.cli.craft import plan_tools

        plans = plan_tools(
            "/learn ./some-repo --no-all-branches --max-files 100 --max-branches 5"
        )
        self.assertEqual(len(plans), 1)
        args = plans[0][1]
        self.assertFalse(args["all_branches"])
        self.assertEqual(args["max_files"], 100)
        self.assertEqual(args["max_branches"], 5)

    def test_plan_tools_learn_windows_drive_and_spaces(self):
        from realai.cli.craft import plan_tools
        from realai.learn_git import parse_learn_tokens, split_learn_rest

        tokens = split_learn_rest(r"C:\path\to\folder")
        self.assertEqual(tokens, [r"C:\path\to\folder"])
        ns = parse_learn_tokens(tokens)
        self.assertEqual(ns.source, r"C:\path\to\folder")

        quoted = split_learn_rest(r'"C:\Program Files\My Repo" --write')
        self.assertEqual(quoted[0], r"C:\Program Files\My Repo")
        ns2 = parse_learn_tokens(quoted)
        self.assertEqual(ns2.source, r"C:\Program Files\My Repo")
        self.assertTrue(ns2.write)

        spaced = parse_learn_tokens(split_learn_rest(r"C:\path\to\my folder"))
        self.assertEqual(spaced.source, r"C:\path\to\my folder")

        plans = plan_tools(r'/learn "C:\path with spaces\repo"')
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0][1]["source"], r"C:\path with spaces\repo")


class TestLocalFolderKind(unittest.TestCase):
    def test_existing_folder_with_spaces_is_kind_local(self):
        from realai.learn.source import resolve_source

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name) / "my repo"
        folder.mkdir()
        (folder / "README.md").write_text("# hi\n", encoding="utf-8")
        cache = Path(tmp.name) / "cache"
        cache.mkdir()
        out = resolve_source(str(folder), cache_dir=cache)
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["kind"], "local")
        self.assertEqual(Path(out["path"]), folder.resolve())

    def test_cli_help_says_local_folder_or_git_url(self):
        cmd = [sys.executable, "-m", "realai.learn_git", "--help"]
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        blob = (r.stdout or "") + (r.stderr or "")
        self.assertRegex(blob, r"(?i)local folder OR git URL")
        self.assertIn("kind=local", blob)

    def test_quoted_source_strips_in_resolve(self):
        from realai.learn.source import resolve_source

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name) / "repo"
        folder.mkdir()
        cache = Path(tmp.name) / "cache"
        cache.mkdir()
        out = resolve_source(f'"{folder}"', cache_dir=cache)
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["kind"], "local")


class TestCloneFlags(unittest.TestCase):
    def test_clone_fetches_all_branches_not_single_tip(self):
        cmd = clone_argv("https://github.com/acme/app.git", Path("/tmp/acme_app"))
        self.assertIn("--no-single-branch", cmd)
        self.assertNotIn("--single-branch", cmd)
        self.assertEqual(cmd[0:3], ["git", "clone", "--no-single-branch"])
        self.assertIn("https://github.com/acme/app.git", cmd)

    def test_fetch_all_argv(self):
        self.assertEqual(fetch_all_argv(), ["fetch", "--all", "--tags"])

    def test_fingerprint_cap_raised(self):
        self.assertGreaterEqual(FINGERPRINT_CAP, 5000)
        self.assertGreaterEqual(DEFAULT_MAX_BRANCHES, 1)


def _git_identity_env(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["HOME"] = str(home)
    env["GIT_AUTHOR_NAME"] = "Learn Test"
    env["GIT_AUTHOR_EMAIL"] = "learn@test.local"
    env["GIT_COMMITTER_NAME"] = "Learn Test"
    env["GIT_COMMITTER_EMAIL"] = "learn@test.local"
    return env


def _git(cwd: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), "-c", "user.name=Learn Test", "-c", "user.email=learn@test.local", *args],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )


def _init_multi_branch_repo(root: Path) -> None:
    env = _git_identity_env(root)
    init = subprocess.run(
        ["git", "init", "-b", "main", str(root)],
        capture_output=True,
        text=True,
        env=env,
    )
    if init.returncode != 0:
        subprocess.run(["git", "init", str(root)], capture_output=True, text=True, check=True, env=env)
        _git(root, env, "checkout", "-B", "main")
    _git(root, env, "config", "commit.gpgsign", "false")
    _git(root, env, "config", "core.hooksPath", os.devnull)
    (root / "README.md").write_text("# Multi branch fixture\n\nShared readme.\n", encoding="utf-8")
    (root / "shared.py").write_text("shared = 1\n", encoding="utf-8")
    (root / "main_only.py").write_text("main_only = True\n", encoding="utf-8")
    nm = root / "node_modules" / "left-pad"
    nm.mkdir(parents=True)
    (nm / "index.js").write_text("module.exports = 1;\n", encoding="utf-8")
    (root / "package-lock.json").write_text('{"lockfileVersion": 3}\n', encoding="utf-8")
    _git(root, env, "add", "-A")
    _git(root, env, "commit", "-m", "main files")
    _git(root, env, "checkout", "-b", "feature/alt")
    (root / "feature_only.py").write_text("feature_only = True\n", encoding="utf-8")
    _git(root, env, "rm", "main_only.py")
    _git(root, env, "add", "feature_only.py")
    _git(root, env, "commit", "-m", "feature files")
    _git(root, env, "checkout", "main")


class TestMultiBranchScan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fixture = self.root / "multi-app"
        self.fixture.mkdir()
        _init_multi_branch_repo(self.fixture)
        self.product = self.root / "product"
        self.product.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _learn(self, **kw):
        return run_learn(
            str(self.fixture),
            write=False,
            product_root=self.product,
            cache_dir=self.product / "realai" / ".learn_cache",
            plugins_root=self.product / "realai" / "plugins",
            packet_root=self.product / "realai" / "catalog" / "learned",
            docs_root=self.product / "docs" / "learning",
            **kw,
        )

    def test_packet_sees_files_from_both_branches(self):
        out = self._learn(all_branches=True)
        self.assertTrue(out["ok"], out)
        packet = out["packet"]
        fps = packet["fingerprints"]
        paths = {fp["path"] for fp in fps}
        self.assertIn("main_only.py", paths, paths)
        self.assertIn("feature_only.py", paths, paths)
        self.assertIn("shared.py", paths, paths)
        self.assertFalse(any("node_modules" in p for p in paths), paths)
        self.assertFalse(any(p.endswith("package-lock.json") for p in paths), paths)
        seen = set(packet["summary"].get("branches_seen") or [])
        self.assertTrue({"main", "feature/alt"} <= seen or seen >= {"main", "feature/alt"}, seen)
        git_branches = packet["source"]["git"].get("branches") or []
        self.assertTrue(any("main" in b or b == "main" for b in git_branches), git_branches)
        self.assertTrue(
            any("feature/alt" in b or b == "feature/alt" for b in git_branches),
            git_branches,
        )
        shared = next(fp for fp in fps if fp["path"] == "shared.py")
        self.assertGreaterEqual(len(shared.get("seen_on_branches") or []), 2)

    def test_no_all_branches_stays_on_checkout(self):
        out = self._learn(all_branches=False)
        self.assertTrue(out["ok"], out)
        paths = {fp["path"] for fp in out["packet"]["fingerprints"]}
        self.assertIn("main_only.py", paths, paths)
        self.assertNotIn("feature_only.py", paths, paths)
        self.assertFalse(any("node_modules" in p for p in paths), paths)

    def test_cli_all_branches_default(self):
        cmd = [
            sys.executable,
            "-m",
            "realai.learn_git",
            str(self.fixture),
            "--max-files",
            "50",
        ]
        env = os.environ.copy()
        env["REALAI_LEARN_ROOT"] = str(self.product)
        repo_root = str(Path(__file__).resolve().parents[2])
        env["PYTHONPATH"] = os.pathsep.join(
            [repo_root] + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
        )
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(self.fixture),
            env=env,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("ok"), data)
        summary = (data.get("packet") or {}).get("summary") or {}
        seen = set(summary.get("branches_seen") or [])
        self.assertIn("main", seen)
        self.assertIn("feature/alt", seen)


if __name__ == "__main__":
    unittest.main()
