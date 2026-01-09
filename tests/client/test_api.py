from __future__ import annotations

import json
from pathlib import Path

import pytest

from fastmail_mcp.client import FastmailClient
from fastmail_mcp.client.transport import FastmailTransportError


class DummyTransport:
    def __init__(
        self,
        *,
        message_responses: list[dict] | None = None,
        contact_responses: list[dict] | None = None,
        event_responses: list[dict] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._message_responses = message_responses or []
        self._contact_responses = contact_responses or []
        self._event_responses = event_responses or []
        self._error = error
        self.calls: dict[str, list[dict]] = {
            "messages": [],
            "contacts": [],
            "events": [],
        }

    def list_messages(self, *, limit: int):
        self._maybe_raise()
        self.calls["messages"].append({"limit": limit})
        return self._message_responses

    def list_contacts(self, *, limit: int):
        self._maybe_raise()
        self.calls["contacts"].append({"limit": limit})
        return self._contact_responses

    def list_events(self, *, limit: int):
        self._maybe_raise()
        self.calls["events"].append({"limit": limit})
        return self._event_responses

    def _maybe_raise(self) -> None:
        if self._error:
            raise self._error


@pytest.fixture()
def sample_payload(tmp_path: Path) -> Path:
    payload = [
        {
            "id": "msg_1",
            "subject": "First",
            "snippet": "Hello",
            "received_at": "2024-01-01T00:00:00+00:00",
        },
        {
            "id": "msg_2",
            "subject": "Second",
            "snippet": "World",
            "received_at": "2024-01-02T00:00:00+00:00",
        },
    ]
    sample_file = tmp_path / "messages.json"
    sample_file.write_text(json.dumps(payload), encoding="utf-8")
    return sample_file


def test_list_recent_messages_uses_transport(sample_payload: Path) -> None:
    transport = DummyTransport(
        message_responses=[
            {
                "id": "live_2",
                "subject": "Newest",
                "snippet": "World",
                "received_at": "2024-01-02T00:00:00+00:00",
            },
            {
                "id": "live_1",
                "subject": "Older",
                "snippet": "Hello",
                "received_at": "2024-01-01T00:00:00+00:00",
            },
        ]
    )
    client = FastmailClient(
        base_url="https://api.example.com",
        username="tester",
        app_password="secret",
        sample_path=sample_payload,
        transport=transport,
    )
    results = client.list_recent_messages(limit=1)
    assert len(results) == 1
    assert results[0].subject == "Newest"
    assert transport.calls["messages"] == [{"limit": 1}]


def test_list_recent_messages_falls_back_to_fixtures(sample_payload: Path) -> None:
    transport = DummyTransport(error=FastmailTransportError("network failure"))
    client = FastmailClient(
        base_url="https://api.example.com",
        username="tester",
        app_password="secret",
        sample_path=sample_payload,
        transport=transport,
    )
    results = client.list_recent_messages(limit=2)
    assert [message.subject for message in results] == ["Second", "First"]


def test_list_recent_messages_requires_sample_file(tmp_path: Path) -> None:
    transport = DummyTransport(error=FastmailTransportError("network failure"))
    client = FastmailClient(
        base_url="https://api.example.com",
        username="tester",
        app_password="secret",
        sample_path=tmp_path / "missing.json",
        transport=transport,
    )
    with pytest.raises(FileNotFoundError):
        client.list_recent_messages()


@pytest.fixture()
def contacts_sample(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    payload = [
        {
            "id": "c1",
            "name": "Ada Lovelace",
            "emails": [{"value": "ada@example.com"}],
        },
        {
            "id": "c2",
            "name": "Grace Hopper",
            "emails": [{"value": "grace@example.com"}],
        },
    ]
    sample_file = tmp_path / "contacts.json"
    sample_file.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("FASTMAIL_CONTACT_SAMPLE_DATA", str(sample_file))
    return sample_file


@pytest.fixture()
def events_sample(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    payload = [
        {
            "id": "e1",
            "title": "Standup",
            "start": "2024-07-02T09:00:00+00:00",
            "end": "2024-07-02T09:15:00+00:00",
        },
        {
            "id": "e2",
            "title": "Retro",
            "start": "2024-07-03T17:00:00+00:00",
            "end": "2024-07-03T18:00:00+00:00",
        },
    ]
    sample_file = tmp_path / "events.json"
    sample_file.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("FASTMAIL_EVENT_SAMPLE_DATA", str(sample_file))
    return sample_file


def test_list_recent_contacts_uses_transport(contacts_sample: Path) -> None:
    transport = DummyTransport(
        contact_responses=[
            {
                "id": "c-live",
                "name": "Zelda Fitzgerald",
                "emails": [{"value": "zelda@example.com"}],
            }
        ]
    )
    client = FastmailClient(
        base_url="https://api.example.com",
        username="tester",
        app_password="secret",
        transport=transport,
    )
    results = client.list_recent_contacts(limit=1)
    assert len(results) == 1
    assert results[0].display_name == "Zelda Fitzgerald"
    assert transport.calls["contacts"] == [{"limit": 1}]


def test_list_recent_contacts_falls_back_to_fixtures(contacts_sample: Path) -> None:
    transport = DummyTransport(error=FastmailTransportError("down"))
    client = FastmailClient(
        base_url="https://api.example.com",
        username="tester",
        app_password="secret",
        transport=transport,
    )
    results = client.list_recent_contacts(limit=2)
    assert [contact.display_name for contact in results] == ["Ada Lovelace", "Grace Hopper"]


def test_list_upcoming_events_uses_transport(events_sample: Path) -> None:
    transport = DummyTransport(
        event_responses=[
            {
                "id": "e-live",
                "title": "Launch",
                "start": "2024-07-04T15:00:00+00:00",
                "end": "2024-07-04T16:00:00+00:00",
            }
        ]
    )
    client = FastmailClient(
        base_url="https://api.example.com",
        username="tester",
        app_password="secret",
        transport=transport,
    )
    results = client.list_upcoming_events(limit=1)
    assert len(results) == 1
    assert results[0].title == "Launch"
    assert transport.calls["events"] == [{"limit": 1}]


def test_list_upcoming_events_falls_back_to_fixtures(events_sample: Path) -> None:
    transport = DummyTransport(error=FastmailTransportError("down"))
    client = FastmailClient(
        base_url="https://api.example.com",
        username="tester",
        app_password="secret",
        transport=transport,
    )
    results = client.list_upcoming_events(limit=2)
    assert [event.title for event in results] == ["Standup", "Retro"]
