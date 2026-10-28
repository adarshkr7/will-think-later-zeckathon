import pytest

from prahari.eval.preregistration import freeze, verify
from prahari.eval.seal import evaluate_final_sealed


def test_registration_failure_does_not_create_a_lock(config, tmp_path, monkeypatch):
    config.base["paths"]["preregistration_lock"] = str(tmp_path / "lock.json")
    def fail(_):
        raise RuntimeError("Panel evidence is incomplete")
    monkeypatch.setattr("prahari.eval.preregistration.preflight", fail)
    with pytest.raises(RuntimeError, match="Panel evidence"):
        freeze(config)
    assert not config.path("preregistration_lock").exists()
    with pytest.raises(RuntimeError, match="replay is prohibited"):
        verify(config)


def test_sealed_preconditions_fail_before_any_protected_access(config, monkeypatch):
    def fail(_):
        raise RuntimeError("public registration required")
    monkeypatch.setattr("prahari.eval.preregistration.verify", fail)
    protected = config.path("indian_sealed_input")
    def forbidden(*args, **kwargs):
        raise AssertionError("Protected source must not be read")
    monkeypatch.setattr("prahari.eval.seal.sha256_file", forbidden)
    monkeypatch.setattr("prahari.eval.seal.pd.read_parquet", forbidden)
    with pytest.raises(RuntimeError, match="public registration"):
        evaluate_final_sealed(config)
