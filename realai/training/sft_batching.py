"""Batching for train_sft: length-bucketed micro-batches, optional packing, length stats. Pure Python (no torch).

A *unit* is what one forward pass sees: a list of sequences (the micro-batch); each sequence is a list of
segments ``(ids, labels)`` - one segment normally, several when packed. Every segment is one dataset row and
keeps its own loss weight (each row's mean token loss counts once, exactly as in the one-row-at-a-time loop).
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Sequence, Tuple

Row = Tuple[List[int], List[int]]
Seq = List[Row]
Unit = List[Seq]


def percentile(sorted_vals: Sequence[int], pct: float) -> int:
    if not sorted_vals:
        return 0
    k = max(0, min(len(sorted_vals) - 1, math.ceil(pct / 100.0 * len(sorted_vals)) - 1))
    return int(sorted_vals[k])


def length_stats(lengths: Sequence[int], max_len: int = 0) -> Dict[str, float]:
    s = sorted(int(x) for x in lengths)
    if not s:
        return {"rows": 0}
    out = {"rows": len(s), "mean": round(sum(s) / len(s), 1), "min": s[0], "p50": percentile(s, 50),
           "p90": percentile(s, 90), "p95": percentile(s, 95), "p99": percentile(s, 99), "max": s[-1],
           "tokens": sum(s)}
    if max_len:
        out["over_max_len"] = sum(1 for x in s if x > max_len)
        kept = [min(x, max_len) for x in s]
        out["pad_to_max_len_efficiency"] = round(sum(kept) / (len(s) * max_len), 3)
    return out


def cap_from_percentile(lengths: Sequence[int], pct: float, max_len: int, floor: int = 256, multiple: int = 64) -> int:
    """max_len chosen from the pct-th length, rounded up to a multiple of 64, within [floor, max_len]."""
    p = percentile(sorted(lengths), pct)
    cap = int(math.ceil(max(p, 1) / multiple) * multiple)
    return max(min(floor, max_len), min(max_len, cap))


def _order(n: int, seed: int) -> List[int]:
    idx = list(range(n))
    random.Random(seed).shuffle(idx)  # same permutation as random.Random(seed).shuffle(rows) in the one-row loop
    return idx


def _group(seqs: List[Seq], batch_size: int, token_budget: int) -> List[Unit]:
    """Sorted sequences -> micro-batches of <= batch_size sequences and <= token_budget padded tokens."""
    units: List[Unit] = []
    cur: List[Seq] = []
    cur_max = 0
    for seq in sorted(seqs, key=lambda q: sum(len(i) for i, _ in q)):
        n = sum(len(i) for i, _ in seq)
        m = max(cur_max, n)
        if cur and (len(cur) >= batch_size or (token_budget and (len(cur) + 1) * m > token_budget)):
            units.append(cur)
            cur, m = [], n
        cur.append(seq)
        cur_max = m
    if cur:
        units.append(cur)
    return units


def bucket_batches(rows: Sequence[Row], batch_size: int, seed: int, window: int = 0, token_budget: int = 0) -> List[Unit]:
    """Micro-batches whose rows have similar lengths, padded only to the micro-batch's longest row.

    The rows are shuffled exactly like the one-row loop and cut into windows of ``window`` rows (one optimizer
    step each), so every step trains on the same rows as before; inside a window rows are sorted by length and
    grouped into micro-batches of <= batch_size rows and <= token_budget padded tokens (0 = no budget)."""
    idx = _order(len(rows), seed)
    if batch_size <= 1 and not token_budget:
        return [[[rows[i]]] for i in idx]
    window = window or max(batch_size, 1) * 50
    rng = random.Random(seed + 7919)
    units: List[Unit] = []
    for c in range(0, len(idx), window):
        part = _group([[rows[i]] for i in idx[c:c + window]], max(batch_size, 1), token_budget)
        rng.shuffle(part)  # order inside a step does not change its gradient
        units += part
    return units


def pack_rows(rows: Sequence[Row], max_len: int, seed: int, batch_size: int = 1, window: int = 0,
              token_budget: int = 0) -> List[Unit]:
    """Like bucket_batches, but rows of a window are first packed (first-fit decreasing) into sequences of
    <= max_len tokens; each row stays its own segment (own positions, own attention block, own loss weight)."""
    idx = _order(len(rows), seed)
    window = window or len(idx) or 1
    units: List[Unit] = []
    for c in range(0, len(idx), window):
        part = sorted(idx[c:c + window], key=lambda i: -len(rows[i][0]))
        bins: List[List[int]] = []
        space: List[int] = []
        for i in part:
            n = len(rows[i][0])
            for b, free in enumerate(space):
                if n <= free:
                    bins[b].append(i)
                    space[b] -= n
                    break
            else:
                bins.append([i])
                space.append(max_len - n)
        units += _group([[rows[i] for i in b] for b in bins], max(batch_size, 1), token_budget)
    return units


def unit_rows(unit: Unit) -> int:
    return sum(len(seq) for seq in unit)


def unit_shape(unit: Unit) -> Tuple[int, int, int]:
    """(batch, padded length, real tokens)."""
    lens = [sum(len(ids) for ids, _ in seq) for seq in unit]
    return len(unit), max(lens) if lens else 0, sum(lens)


def efficiency(units: Sequence[Unit]) -> float:
    real = padded = 0
    for u in units:
        b, L, t = unit_shape(u)
        real += t
        padded += b * L
    return round(real / padded, 3) if padded else 1.0
