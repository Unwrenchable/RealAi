"""Exact (normalized hash) and near-duplicate (MinHash + LSH) removal. Pure Python."""
from __future__ import annotations

import hashlib
import re
import struct
from typing import Dict, List, Sequence, Set, Tuple

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s<>]")


def normalize(text: str) -> str:
    return _WS.sub(" ", _PUNCT.sub(" ", (text or "").lower())).strip()


def exact_key(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def _shingles(text: str, k: int = 5) -> Set[str]:
    words = normalize(text).split()
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def _h(s: str, seed: int) -> int:
    return struct.unpack("<Q", hashlib.blake2b(s.encode("utf-8"), digest_size=8, key=seed.to_bytes(8, "little")).digest())[0]


def minhash(text: str, num_perm: int = 64) -> Tuple[int, ...]:
    sh = _shingles(text)
    if not sh:
        return tuple([0] * num_perm)
    return tuple(min(_h(s, seed) for s in sh) for seed in range(1, num_perm + 1))


def jaccard_est(a: Sequence[int], b: Sequence[int]) -> float:
    return sum(1 for x, y in zip(a, b) if x == y) / float(len(a) or 1)


class NearDedupe:
    """LSH index: bands*rows == num_perm. Default 16x4 catches ~0.85+ similarity."""

    def __init__(self, threshold: float = 0.85, num_perm: int = 64, bands: int = 16):
        self.threshold, self.num_perm, self.bands = threshold, num_perm, bands
        self.rows = num_perm // bands
        self._buckets: List[Dict[Tuple[int, ...], List[int]]] = [dict() for _ in range(bands)]
        self._sigs: List[Tuple[int, ...]] = []

    def add_if_new(self, text: str) -> bool:
        sig = minhash(text, self.num_perm)
        cands: Set[int] = set()
        for b in range(self.bands):
            cands.update(self._buckets[b].get(sig[b * self.rows : (b + 1) * self.rows], ()))
        for c in cands:
            if jaccard_est(sig, self._sigs[c]) >= self.threshold:
                return False
        idx = len(self._sigs)
        self._sigs.append(sig)
        for b in range(self.bands):
            self._buckets[b].setdefault(sig[b * self.rows : (b + 1) * self.rows], []).append(idx)
        return True
