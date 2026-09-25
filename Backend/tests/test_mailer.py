"""Tests unitarios del mailer (SMTP y Mailjet HTTPS, sin red real)."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.domains.usuarios.mail import mailer
from app.domains.usuarios.mail.mailer import (
    MAILJET_REQUEST_TIMEOUT_SEC,
    MAILJET_SEND_URL,
    send_email,
    send_password_reset_code,
    send_test_email,
)

SMTP_ENV = {
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PORT": "587",
    "SMTP_USER": "user@example.com",
    "SMTP_PASS": "smtp-secret",
    "SMTP_FROM": "from@example.com",
}

MAILJET_ENV = {
    "MAIL_PROVIDER": "mailjet",
    "MAILJET_API_KEY": "mj-api-key-test",
    "MAILJET_SECRET_KEY": "mj-secret-key-test",
    "MAILJET_FROM_EMAIL": "digitalizaetl@gmail.com",
}


@contextmanager
def _smtp_server_mock():
    smtp_instance = MagicMock()
    smtp_cm = MagicMock()
    smtp_cm.__enter__.return_value = smtp_instance
    smtp_cm.__exit__.return_value = False
    with patch("app.domains.usuarios.mail.mailer.smtplib.SMTP", return_value=smtp_cm) as smtp_cls:
        yield smtp_cls, smtp_instance


def _mailjet_ok_response(status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = '{"Messages":[{"Status":"success","MessageID":12345}]}'
    response.json.return_value = {"Messages": [{"Status": "success", "MessageID": 12345}]}
    return response


@pytest.fixture
def mail_env(monkeypatch):
    """Limpia variables de mail y permite setear por test."""

    def _apply(overrides: dict[str, str | None]) -> None:
        for key in (
            "MAIL_PROVIDER",
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_USER",
            "SMTP_PASS",
            "SMTP_FROM",
            "MAILJET_API_KEY",
            "MAILJET_SECRET_KEY",
            "MAILJET_FROM_EMAIL",
            "MAILJET_FROM_NAME",
        ):
            monkeypatch.delenv(key, raising=False)
        for key, value in overrides.items():
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, value)

    return _apply


def test_default_provider_uses_smtp(mail_env):
    mail_env(SMTP_ENV)
    with _smtp_server_mock() as (smtp_cls, smtp_instance):
        send_email("dest@example.com", "Asunto", "<p>Hola</p>")
        smtp_cls.assert_called_once()
        smtp_instance.login.assert_called_once()


def test_mail_provider_smtp_explicit(mail_env):
    mail_env({**SMTP_ENV, "MAIL_PROVIDER": "smtp"})
    with _smtp_server_mock() as (smtp_cls, _):
        send_email("dest@example.com", "Asunto", "<p>Hola</p>")
        smtp_cls.assert_called_once()


def test_mail_provider_mailjet_uses_https(mail_env):
    mail_env(MAILJET_ENV)
    with (
        patch("app.domains.usuarios.mail.mailer.requests.post") as post,
        patch("app.domains.usuarios.mail.mailer.smtplib.SMTP") as smtp_cls,
    ):
        post.return_value = _mailjet_ok_response()
        send_email("dest@example.com", "Asunto", "<p>Hola</p>")
        post.assert_called_once()
        smtp_cls.assert_not_called()


def test_unknown_provider_raises(mail_env):
    mail_env({"MAIL_PROVIDER": "sendgrid"})
    with pytest.raises(ValueError, match="MAIL_PROVIDER no soportado"):
        send_email("dest@example.com", "Asunto", "<p>Hola</p>")


@pytest.mark.parametrize(
    "missing_key",
    ["MAILJET_API_KEY", "MAILJET_SECRET_KEY", "MAILJET_FROM_EMAIL"],
)
def test_mailjet_missing_required_env(mail_env, missing_key):
    env = {**MAILJET_ENV}
    env.pop(missing_key)
    mail_env(env)
    with pytest.raises(ValueError, match=missing_key):
        send_email("dest@example.com", "Asunto", "<p>Hola</p>")


def test_mailjet_from_name_defaults_to_digitaliza(mail_env):
    mail_env(MAILJET_ENV)
    with patch("app.domains.usuarios.mail.mailer.requests.post") as post:
        post.return_value = _mailjet_ok_response()
        send_email("dest@example.com", "Asunto", "<p>Hola</p>")
        payload = post.call_args.kwargs["json"]
        assert payload["Messages"][0]["From"]["Name"] == "Digitaliza"


def test_mailjet_request_url_auth_timeout_payload(mail_env):
    mail_env(MAILJET_ENV)
    with patch("app.domains.usuarios.mail.mailer.requests.post") as post:
        post.return_value = _mailjet_ok_response(201)
        send_email("dest@example.com", "Mi asunto", "<p>HTML</p>")
        kwargs = post.call_args.kwargs
        assert post.call_args.args[0] == MAILJET_SEND_URL
        assert kwargs["auth"] == ("mj-api-key-test", "mj-secret-key-test")
        assert kwargs["timeout"] == MAILJET_REQUEST_TIMEOUT_SEC
        msg = kwargs["json"]["Messages"][0]
        assert msg["From"]["Email"] == MAILJET_ENV["MAILJET_FROM_EMAIL"]
        assert msg["From"]["Name"] == "Digitaliza"
        assert msg["To"][0]["Email"] == "dest@example.com"
        assert msg["Subject"] == "Mi asunto"
        assert msg["HTMLPart"] == "<p>HTML</p>"


@pytest.mark.parametrize("status_code", [200, 201, 204])
def test_mailjet_2xx_success(mail_env, status_code):
    mail_env(MAILJET_ENV)
    with patch("app.domains.usuarios.mail.mailer.requests.post") as post:
        post.return_value = _mailjet_ok_response(status_code)
        send_email("dest@example.com", "Asunto", "<p>Hola</p>")


@pytest.mark.parametrize("status_code", [400, 401, 403, 429, 500])
def test_mailjet_http_errors_raise(mail_env, status_code):
    mail_env(MAILJET_ENV)
    with patch("app.domains.usuarios.mail.mailer.requests.post") as post:
        response = MagicMock()
        response.status_code = status_code
        response.text = '{"ErrorInfo":"bad"}'
        post.return_value = response
        with pytest.raises(RuntimeError, match="Mailjet respondió HTTP"):
            send_email("dest@example.com", "Asunto", "<p>Hola</p>")


def test_mailjet_timeout_raises(mail_env):
    mail_env(MAILJET_ENV)
    with patch("app.domains.usuarios.mail.mailer.requests.post") as post:
        post.side_effect = requests.Timeout("timed out")
        with pytest.raises(requests.Timeout):
            send_email("dest@example.com", "Asunto", "<p>Hola</p>")


def test_mailjet_connection_error_raises(mail_env):
    mail_env(MAILJET_ENV)
    with patch("app.domains.usuarios.mail.mailer.requests.post") as post:
        post.side_effect = requests.ConnectionError("network down")
        with pytest.raises(requests.ConnectionError):
            send_email("dest@example.com", "Asunto", "<p>Hola</p>")


def test_mailjet_logs_do_not_contain_secrets(mail_env, capsys):
    mail_env(MAILJET_ENV)
    with patch("app.domains.usuarios.mail.mailer.requests.post") as post:
        post.return_value = _mailjet_ok_response()
        send_email("dest@example.com", "Asunto", "<p>Hola</p>")
    captured = capsys.readouterr().out + capsys.readouterr().err
    assert "mj-api-key-test" not in captured
    assert "mj-secret-key-test" not in captured

    with patch("app.domains.usuarios.mail.mailer.requests.post") as post:
        response = MagicMock()
        response.status_code = 401
        response.text = "Unauthorized"
        post.return_value = response
        with pytest.raises(RuntimeError):
            send_email("dest@example.com", "Asunto", "<p>Hola</p>")
    captured = capsys.readouterr().out + capsys.readouterr().err
    assert "mj-api-key-test" not in captured
    assert "mj-secret-key-test" not in captured


def test_send_test_email_delegates_to_send_email(mail_env):
    mail_env(MAILJET_ENV)
    with patch.object(mailer, "send_email") as send_mock:
        send_test_email("test@example.com")
        send_mock.assert_called_once()
        assert send_mock.call_args.kwargs["to"] == "test@example.com"


def test_send_password_reset_code_delegates_to_send_email(mail_env):
    mail_env(MAILJET_ENV)
    with patch.object(mailer, "send_email") as send_mock:
        send_password_reset_code("user@example.com", "123456")
        send_mock.assert_called_once()
        assert send_mock.call_args.kwargs["to"] == "user@example.com"
        assert "123456" in send_mock.call_args.kwargs["html"]
