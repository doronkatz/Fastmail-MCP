import argparse


from fastmail_mcp.cli import verify
from fastmail_mcp.client.transport import FastmailTransportError


def test_verify_rejects_placeholder_credentials(monkeypatch):
    monkeypatch.setenv("FASTMAIL_USERNAME", "your.name@fastmail.com")
    monkeypatch.setenv("FASTMAIL_APP_PASSWORD", "app-specific-password")
    monkeypatch.delenv("FASTMAIL_TOKEN", raising=False)
    monkeypatch.setattr("fastmail_mcp.cli.load_env", lambda: {})

    def _boom():
        raise AssertionError(
            "transport should not be built with placeholder credentials"
        )

    monkeypatch.setattr("fastmail_mcp.cli._build_transport", _boom)

    result = verify(argparse.Namespace())

    assert result == 1


def test_verify_accepts_missing_optional_capabilities(monkeypatch):
    class DummyTransport:
        def list_messages(self, *, limit: int):
            return [{"id": "m1"}]

        def list_contacts(self, *, limit: int):
            raise FastmailTransportError(
                "Capability urn:ietf:params:jmap:contacts unavailable for this account"
            )

        def list_events(self, *, limit: int):
            raise FastmailTransportError(
                "Capability urn:ietf:params:jmap:calendars unavailable for this account"
            )

    monkeypatch.setenv("FASTMAIL_TOKEN", "token")
    monkeypatch.setenv("FASTMAIL_USERNAME", "user@example.com")
    monkeypatch.setattr("fastmail_mcp.cli.load_env", lambda: {})
    monkeypatch.setattr("fastmail_mcp.cli._build_transport", lambda: DummyTransport())

    result = verify(argparse.Namespace())

    assert result == 0


def test_verify_fails_on_mail_error(monkeypatch):
    class DummyTransport:
        def list_messages(self, *, limit: int):
            raise FastmailTransportError("bad auth")

    monkeypatch.setenv("FASTMAIL_TOKEN", "token")
    monkeypatch.setattr("fastmail_mcp.cli.load_env", lambda: {})
    monkeypatch.setattr("fastmail_mcp.cli._build_transport", lambda: DummyTransport())

    result = verify(argparse.Namespace())

    assert result == 1


def test_verify_fails_on_optional_non_capability_error(monkeypatch):
    class DummyTransport:
        def list_messages(self, *, limit: int):
            return [{"id": "m1"}]

        def list_contacts(self, *, limit: int):
            raise FastmailTransportError("contacts failure")

        def list_events(self, *, limit: int):
            return [{"id": "e1"}]

    monkeypatch.setenv("FASTMAIL_TOKEN", "token")
    monkeypatch.setattr("fastmail_mcp.cli.load_env", lambda: {})
    monkeypatch.setattr("fastmail_mcp.cli._build_transport", lambda: DummyTransport())

    result = verify(argparse.Namespace())

    assert result == 1
