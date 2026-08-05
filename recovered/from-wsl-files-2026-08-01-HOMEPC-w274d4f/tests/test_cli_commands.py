import contextlib
import io
import json
import subprocess
import tempfile
from pathlib import Path
import unittest

from realai import main as realai_main
from realai.cli.realai_cli import main as cli_main


class TestRealAICommandLineInterface(unittest.TestCase):
    def _capture_help(self, entrypoint):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            result = entrypoint(['--help'])
        self.assertEqual(result, 0)
        return buffer.getvalue()

    def test_top_level_entrypoint_exposes_cli_commands(self):
        output = self._capture_help(realai_main)
        self.assertIn('serve', output)
        self.assertIn('self-improve', output)
        self.assertIn('build-datasets', output)

    def test_cli_module_entrypoint_exposes_cli_commands(self):
        output = self._capture_help(cli_main)
        self.assertIn('extract-data', output)
        self.assertIn('finetune-plan', output)
        self.assertIn('benchmark', output)

    def test_repo_loop_creates_report_for_target_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            tests_dir = repo_path / 'tests'
            tests_dir.mkdir()
            (tests_dir / 'test_smoke.py').write_text(
                'import unittest\n\n\nclass SmokeTest(unittest.TestCase):\n    def test_passes(self):\n        self.assertTrue(True)\n',
                encoding='utf-8',
            )

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                result = cli_main(['repo-loop', str(repo_path), '--report-path', str(repo_path / 'report.json')])

            self.assertEqual(result, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload['repo']['repo_path'], str(repo_path.resolve()))
            self.assertIn('branch', payload['repo'])
            self.assertIn('diff_against_default', payload['repo'])
            self.assertEqual(payload['tests']['returncode'], 0)
            self.assertTrue((repo_path / 'report.json').exists())

    def test_doctor_reports_cli_and_repo_health(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            subprocess.run(['git', 'init'], cwd=str(repo_path), capture_output=True, text=True, check=False)

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                result = cli_main(['doctor', '--repo-path', str(repo_path), '--compare-branch', 'realai'])

            self.assertEqual(result, 0)
            payload = json.loads(buffer.getvalue())
            self.assertTrue(payload['ok'])
            self.assertEqual(payload['repo']['repo_path'], str(repo_path.resolve()))
            self.assertIn('branch', payload['repo'])
            self.assertIn('diff_against_default', payload['repo'])
            self.assertTrue(any(check['name'] == 'realai_cli_help' for check in payload['checks']))


if __name__ == '__main__':
    unittest.main()
