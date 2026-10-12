"""Guard: no NEW byte-identical importable duplicates (current ones are allow-listed in config/canonical_paths.json).

If you intentionally add/remove a duplicate, regenerate:  python -m realai.repo_hygiene.canonical_paths --write
"""
import json
from pathlib import Path

from realai.repo_hygiene import canonical_paths as cp

DATA = json.loads(cp.JSON_PATH.read_text(encoding="utf-8"))


def test_no_new_duplicates():
    allowed = {}
    for g in DATA["groups"]:
        for p in [g["canonical"], *g["duplicates"]]:
            allowed[p] = g["sha256"]
    new = []
    for h, paths in cp.duplicate_groups().items():
        known = [p for p in paths if allowed.get(p) == h]
        if len(known) != len(paths):
            new.append(sorted(set(paths) - set(known)))
    assert not new, ("new importable duplicate(s); import the canonical path instead (docs/CANONICAL_PATHS.md): %s" % new)


def test_canonical_paths_exist_and_unique():
    root = cp.ROOT
    canon = [g["canonical"] for g in DATA["groups"]]
    assert len(canon) == len(set(canon))
    missing = [c for c in canon if not (root / c).is_file()]
    assert not missing, missing


def test_prior_cleanup_respected():
    """Canonical choices must agree with AUTHORITY.md / ONE_TREE (gold never loses to a twin)."""
    for g in DATA["groups"]:
        everything = [g["canonical"], *g["duplicates"]]
        for prefix, _ in cp.PRIOR_RULES:
            if any(p.startswith(prefix) and not p.startswith(cp.DEMOTE) and not cp.SNAPSHOT.search(p) for p in everything):
                assert g["canonical"].startswith(prefix), (g["canonical"], prefix)
                break
        assert not g["canonical"].startswith(("_quarantine/", "_parked/", "recovered/", "imports/"))


def test_choose_rules():
    assert cp.choose(["abilities/rackup/glicko2.py", "realai/plugins/rackup_coach/glicko2.py"])[0] == \
        "realai/plugins/rackup_coach/glicko2.py"
    assert cp.choose(["realai/orchestrators/v3.py", "realai/orchestration/v3.py"])[0] == "realai/orchestration/v3.py"
    assert cp.choose(["agents/x.py", "realai/agent_runtime/from-wsl-20260801/x.py"])[0] == "agents/x.py"
