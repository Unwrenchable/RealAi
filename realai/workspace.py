"""
RealAI Workspace Engine — hard-bound product layout.

REALAI_HOME       Package/install dir          = C:\\RealAI-clean\\realai
REALAI_WORKSPACE  Canonical workspace root     = C:\\RealAI-clean
REALAI_PRODUCT_ROOT  Alias of workspace root   = C:\\RealAI-clean

REALAI_EXTRA_READ_ROOTS / REALAI_EXTRA_WRITE_ROOTS / REALAI_EXTRA_WORKSPACES
  Semicolon-separated absolute peer paths (optional).

Rules:
  - WORKSPACE is ALWAYS the product root (parent of this package).
  - WORKSPACE NEVER falls back to Path.cwd().
  - Nested folders under the product root (including this package dir)
    are NEVER treated as the workspace.
  - HOME is the package directory (this file's parent). If env points at
    the product root, HOME is normalized down to <root>\\realai when that
    package exists.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

_PKG = Path(__file__).resolve().parent
_PRODUCT_ROOT = _PKG.parent.resolve()

_CANONICAL_HOME = _PKG
_CANONICAL_WORKSPACE = _PRODUCT_ROOT


# ------------------------------------------------------------
# PRODUCT ROOT + CLAMP
# ------------------------------------------------------------


def product_root() -> Path:
    """Absolute workspace/product root (C:\\RealAI-clean)."""
    env = (os.environ.get("REALAI_PRODUCT_ROOT") or "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        return clamp_to_product_root(p)
    return _PRODUCT_ROOT


def _truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _looks_like_package_dir(path: Path) -> bool:
    """True when path is the install package dir (…/realai with v3_orchestrator)."""
    try:
        p = path.resolve()
    except OSError:
        return False
    if p == _PKG:
        return True
    return p.name.lower() == "realai" and (p / "v3_orchestrator.py").is_file()


def clamp_to_product_root(path: Path) -> Path:
    """
    Collapse any path inside the product tree to the product root.
    Paths outside the product tree are returned unchanged (peer projects).
    """
    root = _PRODUCT_ROOT
    try:
        p = path.expanduser().resolve()
    except OSError:
        return root
    if p == root:
        return root
    if _looks_like_package_dir(p) or _is_under(p, root):
        return root
    # Explicit env sometimes set to a non-existent nested string — still clamp
    # when the path string starts with the product root prefix.
    try:
        if str(p).lower().startswith(str(root).lower() + os.sep):
            return root
    except Exception:
        pass
    return p


def _normalize_home(path: Path) -> Path:
    """
    HOME = package dir (C:\\RealAI-clean\\realai).

    If caller passes the product root, descend into ``realai`` when present.
    If caller passes a deeper nested path under the package, clamp to package.
    """
    root = _PRODUCT_ROOT
    pkg = _PKG
    try:
        p = path.expanduser().resolve()
    except OSError:
        return pkg
    if p == pkg or _looks_like_package_dir(p):
        return pkg
    if p == root:
        candidate = root / "realai"
        if (candidate / "v3_orchestrator.py").is_file() or (candidate / "__main__.py").is_file():
            return candidate.resolve()
        return pkg
    # Nested under package → package root
    if _is_under(p, pkg):
        return pkg
    # Nested under product but not package (e.g. …/scripts) → package
    if _is_under(p, root):
        return pkg
    return p


# ------------------------------------------------------------
# HOME + PRIMARY WORKSPACE
# ------------------------------------------------------------


def realai_home() -> Path:
    env = (os.environ.get("REALAI_HOME") or os.environ.get("REALAI_ROOT") or "").strip()
    if env:
        return _normalize_home(Path(env))
    return _CANONICAL_HOME


def realai_workspace(explicit: Optional[str] = None) -> Path:
    """
    Resolve the project workspace root.

    Priority:
      1. explicit path (CLI ``-C`` / ``--workspace``)
      2. foreign ``Path.cwd()`` (outside the product tree) — beats a
         product-pinned ``REALAI_WORKSPACE`` (common Windows User env)
      3. ``REALAI_WORKSPACE`` when it points at a foreign/peer project
      4. ``REALAI_WORKSPACE`` / canonical product root when cwd is inside product

    Nested paths *inside* the product tree always clamp up to the product root.
    ``REALAI_HOME`` stays the install package; only WORKSPACE moves for foreign repos.
    """
    if explicit:
        return clamp_to_product_root(Path(explicit))

    try:
        cwd = Path.cwd().resolve()
    except OSError:
        cwd = None

    env_raw = (os.environ.get("REALAI_WORKSPACE") or "").strip()
    env_ws = clamp_to_product_root(Path(env_raw)) if env_raw else None

    def _is_foreign(path: Path) -> bool:
        """True when path is outside the RealAI product tree."""
        try:
            p = path.resolve()
        except OSError:
            return False
        if p == _PRODUCT_ROOT or _is_under(p, _PRODUCT_ROOT):
            return False
        return True

    # Foreign shell cwd wins over sticky User env REALAI_WORKSPACE=C:\RealAI-clean
    if cwd is not None and _is_foreign(cwd):
        if env_ws is not None and _is_foreign(env_ws):
            return env_ws
        return cwd

    if env_ws is not None:
        return env_ws

    return _CANONICAL_WORKSPACE

    return _CANONICAL_WORKSPACE


def apply_workspace(
    workspace: Optional[str] = None, *, home: Optional[str] = None
) -> Tuple[Path, Path]:
    h = _normalize_home(Path(home)) if home else realai_home()
    w = realai_workspace(workspace)
    pr = product_root()

    os.environ["REALAI_HOME"] = str(h)
    os.environ["REALAI_ROOT"] = str(h)
    os.environ["REALAI_PRODUCT_ROOT"] = str(pr)
    os.environ["REALAI_WORKSPACE"] = str(w)

    # PYTHONPATH must include the PRODUCT ROOT only as the RealAI import root:
    #   import realai            → <root>/realai/…
    #   import abilities/core/…  → <root>/abilities, <root>/core, …
    # Do NOT put the package dir (<root>/realai) on PYTHONPATH — that shadows
    # stdlib modules such as logging via <root>/realai/logging/.
    pp = os.environ.get("PYTHONPATH") or ""
    parts = [p for p in pp.split(os.pathsep) if p]
    pkg_s = str(h)
    ordered: list[str] = []
    if str(pr) not in ordered:
        ordered.append(str(pr))
    for p in parts:
        # Drop accidental package-dir entries that shadow stdlib.
        try:
            if Path(p).resolve() == Path(pkg_s).resolve():
                continue
        except OSError:
            pass
        if p not in ordered:
            ordered.append(p)
    os.environ["PYTHONPATH"] = os.pathsep.join(ordered)
    # Keep in-process import path consistent with env.
    import sys

    pr_s = str(pr)
    while pkg_s in sys.path:
        sys.path.remove(pkg_s)
    if pr_s in sys.path:
        sys.path.remove(pr_s)
    sys.path.insert(0, pr_s)
    return h, w


# ------------------------------------------------------------
# EXTRA ROOT PARSERS (READ / WRITE / WORKSPACES)
# ------------------------------------------------------------


def _parse_roots(env_name: str) -> list[Path]:
    raw = (os.environ.get(env_name) or "").strip()
    if not raw:
        return []
    parts = []
    for chunk in raw.replace(";", os.pathsep).split(os.pathsep):
        chunk = chunk.strip().strip('"').strip("'")
        if chunk:
            parts.append(chunk)
    roots = []
    for part in parts:
        try:
            p = Path(part).expanduser().resolve()
        except OSError:
            continue
        if p.exists():
            roots.append(p)
    return roots


def extra_read_roots() -> list[Path]:
    return _parse_roots("REALAI_EXTRA_READ_ROOTS")


def extra_write_roots() -> list[Path]:
    return _parse_roots("REALAI_EXTRA_WRITE_ROOTS")


def extra_workspaces() -> list[Path]:
    """Peer workspaces — never include nested product-package folders."""
    root = product_root()
    out: list[Path] = []
    for p in _parse_roots("REALAI_EXTRA_WORKSPACES"):
        if _looks_like_package_dir(p):
            continue
        if _is_under(p, root) and p != root:
            continue
        out.append(p)
    return out


# ------------------------------------------------------------
# PATH CHECKING
# ------------------------------------------------------------


def _under_any(path: Path, roots: list[Path]) -> bool:
    for r in roots:
        try:
            path.relative_to(r)
            return True
        except ValueError:
            continue
    return False


def safe_under(
    root: Path,
    rel_or_abs: str,
    *,
    allow_extra_read: bool = False,
    allow_extra_write: bool = False,
) -> Tuple[Optional[Path], Optional[str]]:
    root = clamp_to_product_root(Path(root).resolve())
    raw = (rel_or_abs or ".").strip() or "."
    p = Path(raw)
    p = (root / p).resolve() if not p.is_absolute() else p.resolve()

    try:
        p.relative_to(root)
        return p, None
    except ValueError:
        pass

    if allow_extra_read and _under_any(p, extra_read_roots()):
        return p, None

    if allow_extra_write and _under_any(p, extra_write_roots()):
        return p, None

    return None, f"path outside workspace: {raw}"


def safe_under_read(root: Path, rel_or_abs: str) -> Tuple[Optional[Path], Optional[str]]:
    return safe_under(root, rel_or_abs, allow_extra_read=True)


def safe_under_write(root: Path, rel_or_abs: str) -> Tuple[Optional[Path], Optional[str]]:
    return safe_under(root, rel_or_abs, allow_extra_write=True)


# ------------------------------------------------------------
# MULTI-WORKSPACE SUPPORT
# ------------------------------------------------------------


def all_workspaces() -> list[Path]:
    return [realai_workspace()] + extra_workspaces()


def resolve_workspace_index(idx: int) -> Path:
    ws = all_workspaces()
    if idx < 0 or idx >= len(ws):
        raise ValueError(f"workspace index out of range: {idx}")
    return ws[idx]


def workspace_scripts(home: Optional[Path] = None) -> Path:
    """Scripts live on the workspace root (C:\\RealAI-clean\\scripts)."""
    ws = realai_workspace()
    primary = ws / "scripts"
    if primary.is_dir():
        return primary
    # Fallback: package-local scripts copy
    h = home or realai_home()
    alt = h / "scripts"
    return alt if alt.is_dir() else primary


def default_gguf(home: Optional[Path] = None) -> Path:
    h = home or realai_home()
    ws = realai_workspace()
    models_home = h / "models"
    models_ws = ws / "models"
    checkpoints_lora = Path(
        os.environ.get("REALAI_MODELS_DIR") or r"C:\models\checkpoints_lora"
    )
    preferred = [
        os.environ.get("REALAI_GGUF") or "",
        os.environ.get("REALAI_MODEL_PATH") or "",
        os.environ.get("REALAI_HIVE_GGUF") or "",
        str(checkpoints_lora / "qwen2.5-coder-7b-instruct-q5_k_m.gguf"),
        str(checkpoints_lora / "qwen2.5-coder-1.5b-instruct-q5_k_m.gguf"),
        str(checkpoints_lora / "realai-1.0-instruct-Q4_K_M.gguf"),
        str(checkpoints_lora / "Llama-3.2-1B-Instruct-Q4_K_M.gguf"),
        str(models_ws / "qwen2.5-coder-7b-instruct-q5_k_m.gguf"),
        str(models_home / "qwen2.5-coder-7b-instruct-q5_k_m.gguf"),
        str(models_ws / "realai-1.0-instruct-Q4_K_M.gguf"),
        str(models_home / "realai-1.0-instruct-Q4_K_M.gguf"),
        str(models_ws / "Llama-3.2-1B-Instruct-Q4_K_M.gguf"),
        str(models_home / "Llama-3.2-1B-Instruct-Q4_K_M.gguf"),
    ]
    for raw in preferred:
        if not raw:
            continue
        p = Path(raw)
        if not p.is_file() and not p.is_absolute():
            for base in (models_ws, models_home):
                cand = base / Path(raw).name
                if cand.is_file():
                    return cand
            continue
        if p.is_file():
            return p
    if checkpoints_lora.is_dir():
        ggufs = sorted(checkpoints_lora.glob("*.gguf"))
        if ggufs:
            return ggufs[0]
    for models in (models_ws, models_home):
        if models.is_dir():
            ggufs = sorted(models.glob("*.gguf"))
            if ggufs:
                return ggufs[0]
    return models_ws / "qwen2.5-coder-7b-instruct-q5_k_m.gguf"


def is_realai_product_tree(path: Optional[Path] = None) -> bool:
    """True when workspace is the RealAI product repo root."""
    p = clamp_to_product_root((path or realai_workspace()).resolve())
    markers = (
        p / "realai" / "v3_orchestrator.py",
        p / "scripts" / "curated_promote.py",
        p / "config" / "realai_models.json",
        p / "abilities",
        p / "agents" / "agentx" / "agents.json",
    )
    return any(m.exists() for m in markers)


def workspace_banner() -> str:
    h, w = realai_home(), realai_workspace()
    mode = "product" if is_realai_product_tree(w) else "project"
    r = extra_read_roots()
    wr = extra_write_roots()
    ws = extra_workspaces()
    return (
        f"home={h}  workspace={w}  mode={mode}  product_root={product_root()}"
        f"  extra_read={len(r)}  extra_write={len(wr)}  multi_ws={len(ws)}"
    )
