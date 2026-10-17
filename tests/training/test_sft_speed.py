"""train_sft speed knobs: bucketing/packing are pure bookkeeping, the batched loss equals the one-row loss."""
import json
import random

import pytest

from realai.training import sft_batching as sb
from realai.training import train_sft as T


def _rows(n=23, seed=0):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        L = rng.randint(6, 40)
        ids = [rng.randint(1, 60) for _ in range(L)]
        k = rng.randint(2, L - 2)
        out.append((ids, [-100] * k + ids[k:]))
    return out


def test_batch_size_1_keeps_the_original_shuffle_order():
    rows = _rows()
    ref = list(rows)
    random.Random(1337 + 2).shuffle(ref)
    assert [u[0][0] for u in sb.bucket_batches(rows, 1, 1337 + 2)] == ref


def test_bucketing_covers_every_row_once_and_groups_lengths():
    rows = _rows(200)
    units = sb.bucket_batches(rows, 4, 7)
    flat = [r for u in units for seq in u for r in seq]
    assert sorted(map(id, flat)) == sorted(map(id, rows)) and all(len(u) <= 4 for u in units)
    rnd = [[[r] for r in rows[i:i + 4]] for i in range(0, 200, 4)]
    assert sb.efficiency(units) > sb.efficiency(rnd)


@pytest.mark.parametrize("pack", [False, True])
def test_windows_hold_the_same_rows_as_the_one_row_loop(pack):
    rows = _rows(70)
    legacy = [u[0][0] for u in sb.bucket_batches(rows, 1, 99)]
    units = (sb.pack_rows(rows, 80, 99, 4, window=16, token_budget=160) if pack
             else sb.bucket_batches(rows, 8, 99, window=16, token_budget=160))
    got, cur, windows = [], [], []
    for u in units:
        cur += [r for seq in u for r in seq]
        if len(cur) >= 16 or sum(map(len, windows)) + len(cur) == 70:
            assert len(cur) == min(16, 70 - sum(map(len, windows)))  # no micro-batch straddles two steps
            windows.append(cur)
            cur = []
    for w, k in zip(windows, range(0, 70, 16)):
        assert sorted(map(id, w)) == sorted(map(id, legacy[k:k + 16]))
    for u in units:
        b, L, _ = sb.unit_shape(u)
        assert b == 1 or b * L <= 160


def test_packing_respects_max_len_and_keeps_rows():
    rows = _rows(100)
    units = sb.pack_rows(rows, 96, 3, batch_size=2)
    seqs = [seq for u in units for seq in u]
    assert all(sum(len(i) for i, _ in seq) <= 96 for seq in seqs)
    assert sorted(map(id, [r for seq in seqs for r in seq])) == sorted(map(id, rows))
    assert len(seqs) < len(rows) / 2


def test_length_stats_and_cap():
    lens = list(range(1, 101))
    st = sb.length_stats(lens, max_len=64)
    assert (st["p50"], st["p95"], st["p99"], st["max"], st["over_max_len"]) == (50, 95, 99, 100, 36)
    assert sb.cap_from_percentile([300] * 99 + [1000], 99, 1024) == 320
    assert sb.cap_from_percentile([10] * 50, 99, 768) == 256  # never below the floor
    assert sb.cap_from_percentile([2000] * 5, 99, 768) == 768  # never above max_len


def _tiny(attn="eager", seed=0, vocab=64):
    torch = pytest.importorskip("torch")
    tr = pytest.importorskip("transformers")
    cfg = tr.Qwen2Config(vocab_size=vocab, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                         num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=256)
    cfg._attn_implementation = attn
    torch.manual_seed(seed)
    return torch, tr.Qwen2ForCausalLM(cfg)


def _ref(torch, model, rows):
    tot = 0.0
    for ids, lab in rows:
        s, k = T.sft_loss(model, ids, lab, "cpu")
        tot = tot + s / k
    return tot


@pytest.mark.parametrize("attn", ["eager", "sdpa"])
@pytest.mark.parametrize("layout", ["single", "padded", "packed", "packed_batch"])
@pytest.mark.parametrize("select", ["index", "matmul"])
def test_unit_loss_and_grads_match_one_row_loop(attn, layout, select):
    torch, model = _tiny(attn)
    rows = _rows(5, seed=4)
    unit = {"single": [[rows[0]]], "padded": [[r] for r in rows], "packed": [rows],
            "packed_batch": [rows[:2], rows[2:]]}[layout]
    used = [r for seq in unit for r in seq]
    model.zero_grad()
    ref = _ref(torch, model, used)
    ref.backward()
    g_ref = {n: p.grad.clone() for n, p in model.named_parameters() if p.grad is not None}
    model.zero_grad()
    wl, lsum, k = T.sft_loss_unit(model, unit, "cpu", ce_chunk=4, select=select)
    wl.backward()
    assert k == sum(sum(1 for x in lab[1:] if x != -100) for _, lab in used)
    assert abs(wl.item() - ref.item()) < 1e-4
    for n, p in model.named_parameters():
        if n in g_ref:
            assert torch.allclose(p.grad, g_ref[n], atol=1e-5, rtol=1e-4), n


class _Tok:
    pad_token = "<p>"
    eos_token = "<e>"
    pad_token_id = 0

    def apply_chat_template(self, msgs, tokenize=True, add_generation_prompt=False, **kw):
        s = "".join(f"<{m['role'][0]}>{m['content']}|" for m in msgs)
        return [ord(c) % 120 + 1 for c in s + ("<a>" if add_generation_prompt else "")]


def _ds(tmp_path, n=24):
    import hashlib

    d = tmp_path / "ds"
    d.mkdir()
    rng = random.Random(0)
    row = lambda i: {"messages": [{"role": "user", "content": f"question {i} " + "x" * rng.randint(0, 40)},
                                  {"role": "assistant", "content": f"answer {i} " + "y" * rng.randint(1, 30)}]}
    tr = "".join(json.dumps(row(i)) + "\n" for i in range(n))
    ev = "".join(json.dumps(row(1000 + i)) + "\n" for i in range(3))
    (d / "train.jsonl").write_text(tr)
    (d / "eval.jsonl").write_text(ev)
    (d / "manifest.json").write_text(json.dumps({"name": "t", "sha256": {
        "train.jsonl": hashlib.sha256(tr.encode()).hexdigest(), "eval.jsonl": hashlib.sha256(ev.encode()).hexdigest()}}))
    return d


@pytest.mark.parametrize("extra", [[], ["--batch-size", "4", "--grad-accum", "2"],
                                   ["--batch-size", "8", "--grad-accum", "1", "--token-budget", "200", "--select", "matmul"],
                                   ["--batch-size", "2", "--grad-accum", "4", "--pack", "--select", "matmul",
                                    "--no-grad-checkpoint", "--len-pct", "99"]])
def test_bench_end_to_end_on_cpu(tmp_path, monkeypatch, extra):
    torch, model = _tiny(vocab=128)
    tr = pytest.importorskip("transformers")
    pytest.importorskip("peft")
    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    monkeypatch.setattr(tr.AutoTokenizer, "from_pretrained", classmethod(lambda cls, *a, **k: _Tok()))
    monkeypatch.setattr(tr.AutoModelForCausalLM, "from_pretrained", classmethod(lambda cls, *a, **k: model))
    monkeypatch.setattr(T, "pick_device", lambda *a: ("cpu", "cpu"))
    monkeypatch.setattr(T, "choose_dtype", lambda device, want, log: "fp32")
    import realai.training.hf_paths as hp

    monkeypatch.setattr(hp, "resolve_model_path", lambda m: m)
    d = _ds(tmp_path)
    out = tmp_path / "runs" / "b"
    base = ["--grad-accum", "8"] if not extra else []
    assert T.main(["train", "--dataset", str(d), "--out", str(out), "--bench", "2", "--max-len", "512"] + base + extra) == 0
    b = json.loads((out / "bench.json").read_text())
    assert b["steps"] == 2 and b["rows_per_step"] == 8 and b["full_run_steps"] == 9
    assert b["projected_full_run_min"] >= 0 and 0 < b["padding_efficiency"] <= 1
    assert not (out / "adapter_last").exists() and not (out / "adapter_best").exists()
    log = (out / "train.log").read_text()
    assert "lengths {" in log and "BENCH" in log


def test_oom_splits_micro_batch_and_keeps_training(tmp_path, monkeypatch):
    torch, model = _tiny(vocab=128)
    tr = pytest.importorskip("transformers")
    pytest.importorskip("peft")
    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    monkeypatch.setattr(tr.AutoTokenizer, "from_pretrained", classmethod(lambda cls, *a, **k: _Tok()))
    monkeypatch.setattr(tr.AutoModelForCausalLM, "from_pretrained", classmethod(lambda cls, *a, **k: model))
    monkeypatch.setattr(T, "pick_device", lambda *a: ("cpu", "cpu"))
    monkeypatch.setattr(T, "choose_dtype", lambda device, want, log: "fp32")
    import realai.training.hf_paths as hp

    monkeypatch.setattr(hp, "resolve_model_path", lambda m: m)
    real = T.sft_loss_unit

    def flaky(model_, unit, *a, **k):
        if len(unit) > 2:
            raise RuntimeError("Could not allocate tensor. There is not enough GPU video memory available!")
        return real(model_, unit, *a, **k)

    monkeypatch.setattr(T, "sft_loss_unit", flaky)
    d = _ds(tmp_path)
    out = tmp_path / "runs" / "o"
    assert T.main(["train", "--dataset", str(d), "--out", str(out), "--bench", "2", "--batch-size", "8",
                   "--grad-accum", "1", "--max-len", "512"]) == 0
    b = json.loads((out / "bench.json").read_text())
    assert b["speed"]["ooms"] >= 1 and b["skipped_rows"] == 0
    assert "splitting it" in (out / "train.log").read_text()


def test_speed_flags_parse_and_default_off():
    r = T.recipe_from(T.build_parser().parse_args(["train", "--dataset", "x"]))
    assert (r.pack, r.len_pct, r.grad_checkpoint, r.select, r.batch_size, r.token_budget) == (False, 0.0, True, "index", 1, 0)
    a = T.build_parser().parse_args(["train", "--dataset", "x", "--pack", "--len-pct", "99", "--no-grad-checkpoint",
                                     "--select", "matmul", "--bench", "6"])
    r = T.recipe_from(a)
    assert (r.pack, r.len_pct, r.grad_checkpoint, r.select, a.bench) == (True, 99.0, False, "matmul", 6)


def test_bench_report_table(tmp_path, capsys):
    from realai.training import bench_report as br

    for name, s, tps in (("bench-default", 88.0, 220), ("bench-fast", 55.0, 360)):
        d = tmp_path / name
        d.mkdir()
        (d / "bench.json").write_text(json.dumps({"sec_per_step_after_first": s, "tokens_per_s": tps, "peak_vram_gb": 10.1,
                                                  "padding_efficiency": 0.95, "projected_full_run_min": s * 198 / 60,
                                                  "speed": {"ooms": 0}}))
    assert br.main([str(tmp_path / "bench-default"), str(tmp_path / "bench-fast"), str(tmp_path / "missing")]) == 0
    out = capsys.readouterr().out
    assert "1.60x" in out and "1.00x" in out and "skip" in out
