"""SuperGrok auth helpers. No live xAI calls."""

from __future__ import annotations

from app.settings import MODEL_ID, SIGNIN_HINT, default_model, inference_ready
from app.xai_login import main
from workflows.deployment_check import _check_model_auth, _check_openai_optional


def test_default_model_is_grok() -> None:
    model = default_model()
    assert model.id == MODEL_ID
    assert model.token_manager is not None
    assert model.require_user_token is False


def test_login_status_unsigned(monkeypatch, capsys) -> None:
    monkeypatch.setattr("app.xai_login.supergrok_signed_in", lambda: False)
    assert main(["--status"]) == 1
    assert capsys.readouterr().out.strip() == "unsigned"


def test_login_status_signed_in(monkeypatch, capsys) -> None:
    monkeypatch.setattr("app.xai_login.supergrok_signed_in", lambda: True)
    assert main(["--status"]) == 0
    assert capsys.readouterr().out.strip() == "signed-in"


def test_login_requires_encryption_key(monkeypatch, capsys) -> None:
    monkeypatch.setattr("app.xai_login.encryption_key_set", lambda: False)
    assert main([]) == 2
    err = capsys.readouterr().err
    assert "XAI_TOKEN_ENCRYPTION_KEY" in err


def test_model_auth_fails_without_encryption_key(monkeypatch) -> None:
    monkeypatch.setattr("workflows.deployment_check.encryption_key_set", lambda: False)
    check = _check_model_auth()
    assert check.status == "FAIL"
    assert "XAI_TOKEN_ENCRYPTION_KEY" in check.detail


def test_model_auth_pass_when_signed_in(monkeypatch) -> None:
    monkeypatch.setattr("workflows.deployment_check.encryption_key_set", lambda: True)
    monkeypatch.setattr("workflows.deployment_check.supergrok_signed_in", lambda: True)
    check = _check_model_auth()
    assert check.status == "PASS"


def test_model_auth_warns_on_api_key_fallback(monkeypatch) -> None:
    monkeypatch.setattr("workflows.deployment_check.encryption_key_set", lambda: True)
    monkeypatch.setattr("workflows.deployment_check.supergrok_signed_in", lambda: False)
    monkeypatch.setenv("XAI_API_KEY", "xai-test")
    check = _check_model_auth()
    assert check.status == "WARN"
    assert "XAI_API_KEY" in check.detail


def test_model_auth_fails_when_unsigned(monkeypatch) -> None:
    monkeypatch.setattr("workflows.deployment_check.encryption_key_set", lambda: True)
    monkeypatch.setattr("workflows.deployment_check.supergrok_signed_in", lambda: False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    check = _check_model_auth()
    assert check.status == "FAIL"


def test_openai_optional_warns_when_set(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    check = _check_openai_optional()
    assert check.status == "WARN"


def test_inference_ready_needs_session_or_key(monkeypatch) -> None:
    monkeypatch.setattr("app.settings.supergrok_signed_in", lambda: False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    assert inference_ready() is False
    monkeypatch.setenv("XAI_API_KEY", "xai-test")
    assert inference_ready() is True
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setattr("app.settings.supergrok_signed_in", lambda: True)
    assert inference_ready() is True
    assert "xai_login" in SIGNIN_HINT


def test_openai_optional_pass_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    check = _check_openai_optional()
    assert check.status == "PASS"
