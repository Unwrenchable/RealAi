"""Offline tests for the fixed SFT recipe (no torch/transformers needed)."""
import json

import pytest

from realai.training import train_sft as T


class FakeTok:
    """Char-level stand-in for a chat template: <r>content</r> blocks."""

    def apply_chat_template(self, msgs, tokenize=True, add_generation_prompt=False):
        s = "".join(f"<{m['role'][0]}>{m['content']}|" for m in msgs)
        if add_generation_prompt:
            s += "<a>"
        return [ord(c) for c in s]


def _ds(tmp_path, train=3, ev=1):
    from realai.training.dataset_builder import build

    d = tmp_path / "ds"
    d.mkdir()
    row = lambda i: {"messages": [{"role": "user", "content": f"q{i}"}, {"role": "assistant", "content": f"answer {i}"}]}
    tr = "".join(json.dumps(row(i)) + "\n" for i in range(train))
    e = "".join(json.dumps(row(100 + i)) + "\n" for i in range(ev))
    (d / "train.jsonl").write_bytes(tr.encode())
    (d / "eval.jsonl").write_bytes(e.encode())
    import hashlib

    (d / "manifest.json").write_text(json.dumps({"name": "t", "sha256": {
        "train.jsonl": hashlib.sha256(tr.encode()).hexdigest(), "eval.jsonl": hashlib.sha256(e.encode()).hexdigest()}}))
    return d


def test_defaults_are_the_fixed_recipe():
    a = T.build_parser().parse_args(["train", "--dataset", "x"])
    r = T.recipe_from(a)
    assert r.base_model == "Qwen/Qwen2.5-1.5B-Instruct" and r.max_len == 1024
    assert (r.lora_r, r.lora_alpha, r.lora_dropout) == (16, 32, 0.05)
    assert set(r.lora_targets) == {"q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"}
    assert (r.lr, r.warmup_ratio, r.epochs) == (1e-4, 0.03, 3) and r.grad_accum > 1
    assert r.dml_adapter == "RX 6700"


def test_max_len_cannot_be_tiny():
    with pytest.raises(SystemExit):
        T.build_parser().parse_args(["train", "--dataset", "x", "--max-len", "64"])


def test_dry_run_plan(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    d = _ds(tmp_path, train=40)
    assert T.main(["train", "--dataset", str(d), "--dry-run", "--grad-accum", "8"]) == 0
    p = json.loads(capsys.readouterr().out)
    assert p["ok"] and p["dataset"]["train"] == 40 and p["optimizer_steps"]["per_epoch"] == 5
    assert p["optimizer_steps"]["total"] == 15 and p["len_backoff"] == [1024, 768, 512]
    assert not (tmp_path / "runs").exists()  # dry-run writes nothing


def test_dry_run_flags_bad_data(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    d = _ds(tmp_path)
    (d / "eval.jsonl").write_text((d / "train.jsonl").read_text().splitlines()[0] + "\n")
    assert T.main(["plan", "--dataset", str(d)]) == 2
    p = json.loads(capsys.readouterr().out)
    assert any("also in train" in i for i in p["dataset"]["issues"])
    assert any("sha256" in i for i in p["dataset"]["issues"])


def test_refuses_out_outside_home(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    d = _ds(tmp_path)
    with pytest.raises(SystemExit):
        T.main(["plan", "--dataset", str(d), "--out", str(tmp_path / "elsewhere")])


def test_loss_only_on_assistant_tokens():
    tok = FakeTok()
    msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "Q"}, {"role": "assistant", "content": "AB"}]
    ids, lab = T.encode_assistant_only(tok, msgs, 1024)
    target = "".join(chr(x) for x in lab if x != -100)
    assert target == "AB|"  # assistant content + end marker; header and prompt masked
    assert len(ids) == len(lab)
    ids2, lab2 = T.encode_assistant_only(tok, msgs, 5)
    assert len(ids2) == 5 and all(x == -100 for x in lab2)


def test_oom_detection():
    assert T._is_oom(RuntimeError("DML: Could not allocate tensor... not enough memory"))
    assert not T._is_oom(ValueError("shape mismatch"))


def test_sft_loss_matches_reference_ce():
    torch = pytest.importorskip("torch")
    tr = pytest.importorskip("transformers")
    cfg = tr.Qwen2Config(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                         num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=64)
    torch.manual_seed(0)
    model = tr.Qwen2ForCausalLM(cfg).eval()
    ids = list(range(1, 13))
    lab = [-100] * 6 + ids[6:]
    with torch.no_grad():
        ref = model(input_ids=torch.tensor([ids]), labels=torch.tensor([lab])).loss.item()
        s, k = T.sft_loss(model, ids, lab, "cpu")
    assert k == 6 and abs(s.item() / k - ref) < 1e-4


def test_oom_message_from_directml_is_caught():
    assert T._is_oom(RuntimeError("Could not allocate tensor with 515366912 bytes. There is not enough GPU video memory available!"))


def test_max_steps_flag():
    a = T.build_parser().parse_args(["train", "--dataset", "x", "--max-steps", "10", "--eval-smoke", "--eval-rows", "20"])
    assert (a.max_steps, a.eval_smoke, a.eval_rows) == (10, True, 20)


def test_cosine_warmup_curve():
    class O:
        param_groups = [{"lr": 1e-4}]

    o = O()
    s = T.CosineWarmup(o, 10, 100)
    assert o.param_groups[0]["lr"] == 0
    for _ in range(10):
        s.step()
    assert abs(s.get_last_lr()[0] - 1e-4) < 1e-12
    for _ in range(90):
        s.step()
    assert s.get_last_lr()[0] < 1e-12
