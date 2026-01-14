import pytest

from fastmail_mcp.client.transport import (
    FastmailTransportError,
    JMAPTransport,
    JMAP_CALENDAR_CAPABILITY,
    JMAP_CONTACTS_CAPABILITY,
    JMAP_MAIL_CAPABILITY,
)


class FakeResponse:
    def __init__(self, *, status_code: int, json_data: dict, text: str = "") -> None:
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self) -> dict:
        return self._json


class FakeSession:
    def __init__(self, *, session_payload: dict, method_payload: dict) -> None:
        self.session_payload = session_payload
        self.method_payload = method_payload
        self.get_calls = []
        self.post_calls = []

    def get(self, url, auth=None, headers=None, timeout=None):
        self.get_calls.append(
            {
                "url": url,
                "auth": auth,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return FakeResponse(status_code=200, json_data=self.session_payload)

    def post(self, url, json, auth=None, headers=None, timeout=None):
        self.post_calls.append(
            {
                "url": url,
                "json": json,
                "auth": auth,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return FakeResponse(status_code=200, json_data=self.method_payload)


@pytest.fixture()
def session_payload():
    return {
        "apiUrl": "https://api.fastmail.com/jmap/",
        "primaryAccounts": {
            JMAP_MAIL_CAPABILITY: "acc_mail",
            JMAP_CONTACTS_CAPABILITY: "acc_contacts",
            JMAP_CALENDAR_CAPABILITY: "acc_calendar",
        },
    }


@pytest.fixture()
def method_payload():
    return {
        "methodResponses": [
            [
                "Email/get",
                {
                    "list": [
                        {
                            "id": "m1",
                            "subject": "Hi",
                            "preview": "Snippet",
                            "receivedAt": "2024-02-02T00:00:00+00:00",
                        }
                    ]
                },
                "b",
            ]
        ]
    }


@pytest.fixture()
def contacts_method_payload():
    return {
        "methodResponses": [
            [
                "Contact/get",
                {
                    "list": [
                        {
                            "id": "c1",
                            "name": "Ada",
                            "emails": [{"value": "ada@example.com"}],
                        }
                    ]
                },
                "b",
            ]
        ]
    }


@pytest.fixture()
def events_method_payload():
    return {
        "methodResponses": [
            [
                "CalendarEvent/get",
                {
                    "list": [
                        {
                            "id": "e1",
                            "title": "Standup",
                            "start": "2024-07-02T09:00:00+00:00",
                            "end": "2024-07-02T09:15:00+00:00",
                        }
                    ]
                },
                "b",
            ]
        ]
    }


def test_jmap_transport_list_messages(session_payload, method_payload):
    session = FakeSession(
        session_payload=session_payload, method_payload=method_payload
    )
    transport = JMAPTransport(
        base_url="https://api.fastmail.com",
        username="user",
        app_password="secret",
        session=session,
    )

    result = transport.list_messages(limit=5)

    assert session.get_calls[0]["url"].endswith("/.well-known/jmap")
    post_call = session.post_calls[0]
    assert post_call["json"]["methodCalls"][0][1]["limit"] == 5
    assert result[0]["subject"] == "Hi"


def test_jmap_transport_raises_on_error(session_payload):
    session = FakeSession(
        session_payload=session_payload, method_payload={"methodResponses": []}
    )
    transport = JMAPTransport(
        base_url="https://api.fastmail.com",
        username="user",
        app_password="secret",
        session=session,
    )

    with pytest.raises(FastmailTransportError):
        transport.list_messages(limit=1)


def test_jmap_transport_list_contacts(session_payload, contacts_method_payload):
    session = FakeSession(
        session_payload=session_payload, method_payload=contacts_method_payload
    )
    transport = JMAPTransport(
        base_url="https://api.fastmail.com",
        username="user",
        app_password="secret",
        session=session,
    )

    results = transport.list_contacts(limit=3)

    post_call = session.post_calls[0]
    assert post_call["json"]["methodCalls"][0][0] == "Contact/query"
    assert results[0]["name"] == "Ada"


def test_jmap_transport_list_events(session_payload, events_method_payload):
    session = FakeSession(
        session_payload=session_payload, method_payload=events_method_payload
    )
    transport = JMAPTransport(
        base_url="https://api.fastmail.com",
        username="user",
        app_password="secret",
        session=session,
    )

    results = transport.list_events(limit=2)

    post_call = session.post_calls[0]
    assert post_call["json"]["methodCalls"][0][0] == "CalendarEvent/query"
    assert results[0]["title"] == "Standup"


def test_jmap_transport_uses_bearer_token(session_payload, method_payload):
    session = FakeSession(
        session_payload=session_payload, method_payload=method_payload
    )
    transport = JMAPTransport(
        base_url="https://api.fastmail.com",
        username="user",
        app_password="secret",
        token="token123",
        session=session,
    )

    transport.list_messages(limit=1)

    assert session.get_calls[0]["auth"] is None
    assert session.get_calls[0]["headers"]["Authorization"] == "Bearer token123"
