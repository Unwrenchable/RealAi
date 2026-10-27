import json
from pathlib import Path

from realai.training import ledger


def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_MODELS_LEDGER", str(tmp_path / "MODELS.md"))


def _run(tmp_path):
    out = tmp_path / "runs" / "sft-x"
    (out).mkdir(parents=True)
    ds = tmp_path / "ds"; ds.mkdir()
    (ds / "manifest.json").write_text(json.dumps({"sources": {"tool_calls": {"kept": 9}, "off": {"disabled": 1}}}))
    res = {"steps": 6, "sec_per_step": 2.0, "best_eval_loss": 0.5, "history": [{"epoch": 1, "eval_loss": 0.6}, {"epoch": 2, "eval_loss": 0.5}],
           "recipe": {"base_model": "C:/models/hf/Qwen2.5-1.5B-Instruct"},
           "dataset": {"dir": str(ds), "train": 9, "eval": 1, "manifest_name": "hive", "manifest_sha256": "ab"}}
    (out / "train_result.json").write_text(json.dumps(res))
    return out, res


def test_paths_env(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch)
    assert ledger.json_path() == tmp_path / "models_ledger.json"


def test_train_idempotent_and_history(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch)
    out, res = _run(tmp_path)
    assert ledger.on_train(out, res) is True
    assert ledger.on_train(out, res) is False  # no change -> no history
    d = ledger.load()
    assert len(d["history"]) == 1
    e = d["runs"]["x"]
    assert e["status"] == "trained" and e["eval_loss_per_epoch"] == {"1": 0.6, "2": 0.5}
    assert e["dataset"]["source_mix"] == {"tool_calls": 9}
    md = (tmp_path / "MODELS.md").read_text()
    assert "Do not edit by hand" in md and "| x |" in md


def test_export_spotcheck_register_improve(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch)
    out, res = _run(tmp_path)
    ledger.on_train(out, res)
    g = out / "gguf" / "m-Q5_K_M.gguf"; g.parent.mkdir(); g.write_bytes(b"x" * 10)
    ledger.on_export(out, g, "Q5_K_M", "m")
    ledger.on_spotcheck({"use_tools": True, "passed": 3, "n": 16, "pass_rate": 0.19, "ts": "2026-10-10T13:00"}, tmp_path / "r.json", "m")
    ledger.on_spotcheck({"use_tools": False, "passed": 1, "n": 16, "pass_rate": 0.06, "ts": "2026-10-10T13:01"}, tmp_path / "r2.json", "m")
    ledger.on_register(out, {"id": "m", "default": False, "registered_at": "t"})
    ledger.on_improve({"ts": "t", "selfplay_rows_added_recent": 12, "weak": [{"tool": "shot_lookup"}]})
    d = ledger.load()
    e = d["runs"]["x"]
    assert e["spotcheck"]["tools"]["passed"] == 3 and e["spotcheck"]["no_tools"]["passed"] == 1
    assert e["status"] == "registered" and e["default"] is False and "Q5_K_M" in e["gguf"]
    assert d["runs"]["_self_data"]["selfplay_rows_added_recent"] == 12
    md = (tmp_path / "MODELS.md").read_text()
    assert "tools 3/16" in md and "no-tools 1/16" in md and "shot_lookup" in md


def test_spotcheck_unknown_goes_to_baselines_and_seed_idempotent(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch)
    ledger.seed(tmp_path)
    n = len(ledger.load()["history"])
    ledger.seed(tmp_path)
    assert len(ledger.load()["history"]) == n
    ledger.on_spotcheck({"use_tools": True, "passed": 0, "n": 16, "pass_rate": 0, "ts": "t"}, tmp_path / "r.json", "qwen2.5-1.5b-expand-b2-20260927")
    d = ledger.load()
    assert d["baselines"]["qwen2.5-1.5b-expand-b2-20260927"]["spotcheck"]["tools"]["n"] == 16
    md = (tmp_path / "MODELS.md").read_text()
    assert "archived-experiment" in md and "Qwen3-30B-A3B" in md and "## Next" in md


def test_safe_never_raises():
    assert ledger.safe(lambda: 1 / 0) is None
