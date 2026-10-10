import pytest


@pytest.fixture(autouse=True)
def _isolated_model_ledger(tmp_path, monkeypatch):
    """Never let tests write the real C:/models/MODELS.md ledger."""
    monkeypatch.setenv("REALAI_MODELS_LEDGER", str(tmp_path / "ledger" / "MODELS.md"))
