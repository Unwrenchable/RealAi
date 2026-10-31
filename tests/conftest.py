"""Suite-wide guard: tests must never write the tracked model registry.

``realai.models.model_catalog`` persists ``config/realai_models.json`` (and the
product-root twin). Point both at a temp copy for the whole session so no test
can mutate repo files, even by accident.
"""
from __future__ import annotations

import shutil

import pytest


@pytest.fixture(autouse=True, scope="session")
def _isolate_model_registry(tmp_path_factory):
    try:
        from realai.models import model_catalog as mc
    except Exception:  # catalog not importable in this environment
        yield
        return
    tmp = tmp_path_factory.mktemp("model_registry")
    pkg_copy = tmp / "pkg" / "realai_models.json"
    prod_copy = tmp / "product" / "realai_models.json"
    for src, dst in ((mc._REGISTRY, pkg_copy), (mc._PRODUCT_REGISTRY, prod_copy)):
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copyfile(src, dst)
    old = (mc._REGISTRY, mc._PRODUCT_REGISTRY)
    mc._REGISTRY, mc._PRODUCT_REGISTRY = pkg_copy, prod_copy
    try:
        yield
    finally:
        mc._REGISTRY, mc._PRODUCT_REGISTRY = old


@pytest.fixture(autouse=True, scope="session")
def _isolate_approvals_store(tmp_path_factory):
    """Pin the shared approvals store (realai.core.approvals_config) to a temp file on every OS.

    The Windows default is the live queue C:\\RealAI-clean\\.approvals.json; both the env var and the config
    file are redirected so a test that clears the env still lands in temp, never the live store.
    """
    import json
    import os

    tmp = tmp_path_factory.mktemp("approvals")
    store = tmp / ".approvals.json"
    cfg = tmp / "approvals_config.json"
    cfg.write_text(json.dumps({"store": str(store), "store_posix": str(store)}), encoding="utf-8")
    keys = ("REALAI_APPROVALS_STORE", "APPROVALS_STORE", "REALAI_APPROVALS_CONFIG")
    old = {k: os.environ.get(k) for k in keys}
    os.environ["REALAI_APPROVALS_STORE"] = str(store)
    os.environ["APPROVALS_STORE"] = str(store)
    os.environ["REALAI_APPROVALS_CONFIG"] = str(cfg)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.fixture(autouse=True, scope="session")
def _isolate_console_turn_log(tmp_path_factory):
    """Console turn logs (#233) go to a tmp dir, never the repo's logs/."""
    import os

    key = "REALAI_CONSOLE_TURN_LOG_DIR"
    prev = os.environ.get(key)
    os.environ[key] = str(tmp_path_factory.mktemp("console_turns"))
    yield
    if prev is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = prev
