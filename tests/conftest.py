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
