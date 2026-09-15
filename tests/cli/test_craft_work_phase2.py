"""Static tests for Craft Phase 2: foreign /work → coder, unique seeds, synthesis."""
from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

from realai.meta_router import classify_task, plan_call, route_task


WORK_GOAL = "/work shot of the day diagrams and halls map locations"


class TestMetaRouterWorkLoop(unittest.TestCase):
    def test_work_goal_classifies_as_code(self):
        self.assertEqual(classify_task(WORK_GOAL), "code")

    def test_work_goal_routes_coder_not_overseer(self):
        d = route_task(WORK_GOAL)
        self.assertEqual(d.target, "coder")
        self.assertNotEqual(d.reason, "default local hive overseer")
        self.assertIn("coder", d.reason.lower())

    def test_plan_call_work_goal_target_coder(self):
        pc = plan_call(WORK_GOAL, mode="project")
        routing = pc.get("routing") or {}
        self.assertEqual(routing.get("target"), "coder")
        self.assertNotEqual(routing.get("reason"), "default local hive overseer")

    def test_foreign_freetext_inspect_routes_coder(self):
        d = route_task("check halls map locations", mode="project")
        self.assertEqual(d.target, "coder")
        self.assertEqual(d.task_class, "code")

    def test_product_file_ask_routes_coder(self):
        d = route_task("what's in console.html", mode="product")
        self.assertEqual(d.target, "coder")
        self.assertEqual(d.task_class, "code")

    def test_product_smalltalk_stays_overseer(self):
        d = route_task("hello there", mode="product")
        self.assertEqual(d.target, "overseer")
        self.assertEqual(d.reason, "default local hive overseer")


class TestCraftWorkPlans(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._env = {
            k: os.environ.get(k)
            for k in ("REALAI_WORKSPACE", "REALAI_HOME", "REALAI_PRODUCT_ROOT", "REALAI_ROOT")
        }
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._write_rackup_tree(self.root)
        os.environ["REALAI_WORKSPACE"] = str(self.root)
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self._cwd)
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp.cleanup()

    @staticmethod
    def _write_rackup_tree(root: Path) -> None:
        files = [
            "rackup-backend/src/realai/v2/sotd-shot-maps.ts",
            "rackup-web/src/components/ShotMapDiagram.tsx",
            "rackup-web/src/lib/shot-map-geometry.ts",
            "rackup-backend/src/shots/shot-catalog.ts",
            "rackup-web/src/components/HallsMap.tsx",
            "rackup-web/src/pages/HallsPage.tsx",
        ]
        for rel in files:
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"// {rel}\nexport const lat = 1;\n", encoding="utf-8")
        (root / "package.json").write_text(
            '{"name":"rack-em-up","platform":"node"}\n',
            encoding="utf-8",
        )
        (root / "src").mkdir(exist_ok=True)
        (root / "rackup-web" / "src" / "HallsMap.tsx").write_text(
            "import mapbox from 'mapbox-gl';\n",
            encoding="utf-8",
        )

    def test_work_seed_reads_are_unique(self):
        from realai.cli.craft import plan_tools

        plans = plan_tools(WORK_GOAL)
        reads = [kw.get("path") for name, kw in plans if name == "read"]
        norm = [str(p).replace("\\", "/").lower() for p in reads]
        self.assertEqual(len(norm), len(set(norm)), f"duplicate reads: {reads}")
        self.assertGreaterEqual(len(reads), 4)

    def test_keyword_grep_word_bounds_lat(self):
        from realai.cli.craft import _keyword_grep_pattern

        pat = _keyword_grep_pattern("halls map locations")
        self.assertIn(r"\blat\b", pat)
        self.assertIsNone(re.search(pat, '{"platform":"node"}', re.I))
        self.assertIsNotNone(re.search(pat, "const lat = 32.1", re.I))

    def test_grep_skips_package_json_platform_noise(self):
        from realai.cli.craft import tool_grep

        r = tool_grep(pattern=r"lat|mapbox|platform", max_hits=40)
        files = [str(h.get("file") or "").replace("\\", "/") for h in (r.get("hits") or [])]
        self.assertFalse(any(f.endswith("package.json") or f == "package.json" for f in files), files)

    def test_post_tool_prompt_asks_for_patches(self):
        from realai.cli.craft import build_messages

        msgs = build_messages(
            WORK_GOAL,
            [],
            [
                {
                    "tool": "read",
                    "result": {
                        "path": "rackup-web/src/components/HallsMap.tsx",
                        "content": "export function HallsMap() {}",
                    },
                }
            ],
        )
        blob = "\n".join(m.get("content") or "" for m in msgs)
        self.assertIn("Synthesize a short diagnosis", blob)
        self.assertIn("/write", blob)
        self.assertNotIn("Reply for this project workspace.", blob)

    def test_extract_and_apply_write_block(self):
        from realai.cli.craft import apply_suggested_writes, extract_write_commands

        reply = (
            "Halls map is in HallsMap.tsx.\n"
            "/write rackup-web/src/components/HallsMap.tsx|||\n"
            "export function HallsMap() { return null; }\n"
        )
        blocks = extract_write_commands(reply)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0][0], "rackup-web/src/components/HallsMap.tsx")
        applied = apply_suggested_writes(reply)
        self.assertEqual(len(applied), 1)
        result = applied[0].get("result") or {}
        self.assertTrue(result.get("ok"), result)
        written = (self.root / "rackup-web/src/components/HallsMap.tsx").read_text(encoding="utf-8")
        self.assertIn("return null", written)


if __name__ == "__main__":
    unittest.main()
