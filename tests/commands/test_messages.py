import json
from pathlib import Path

import pytest

from fastmail_mcp.client import FastmailClient
from fastmail_mcp.commands import messages
from fastmail_mcp.server import FastmailMCPServer


class DummyTransport:
    def __init__(self, responses: list[dict]):
        self.responses = responses

    def list_messages(self, *, limit: int):
        return self.responses


@pytest.fixture()
def sample_payload(tmp_path: Path) -> Path:
    payload = [
        {
            "id": "msg_a",
            "subject": "Second",
            "snippet": "Second message",
            "received_at": "2024-05-02T10:00:00+00:00",
        },
        {
            "id": "msg_b",
            "subject": "Latest",
            "snippet": "Latest message",
            "received_at": "2024-05-03T10:00:00+00:00",
        },
        {
            "id": "msg_c",
            "subject": "Oldest",
            "snippet": "Old message",
            "received_at": "2024-05-01T10:00:00+00:00",
        },
    ]
    sample_file = tmp_path / "messages.json"
    sample_file.write_text(json.dumps(payload), encoding="utf-8")
    return sample_file


def build_server(sample_path: Path) -> FastmailMCPServer:
    transport = DummyTransport(
        [
            {
                "id": "msg_b",
                "subject": "Latest",
                "snippet": "Latest message",
                "received_at": "2024-05-03T10:00:00+00:00",
            },
            {
                "id": "msg_a",
                "subject": "Second",
                "snippet": "Second message",
                "received_at": "2024-05-02T10:00:00+00:00",
            },
            {
                "id": "msg_c",
                "subject": "Oldest",
                "snippet": "Old message",
                "received_at": "2024-05-01T10:00:00+00:00",
            },
        ]
    )
    client = FastmailClient(
        base_url="https://api.example.com",
        username="tester",
        app_password="secret",
        sample_path=sample_path,
        transport=transport,
    )
    server = FastmailMCPServer(client)
    messages.register(server, client)
    return server


def test_messages_list_returns_sorted_results(sample_payload: Path) -> None:
    server = build_server(sample_payload)
    response = server.handle_request(
        {
            "command": messages.COMMAND_MESSAGES_LIST,
            "params": {"limit": 2},
        }
    )
    assert response["command"] == messages.COMMAND_MESSAGES_LIST
    result = response["result"]
    assert result["count"] == 2
    subjects = [message["subject"] for message in result["messages"]]
    assert subjects == ["Latest", "Second"]


def test_invalid_limit_raises_error(sample_payload: Path) -> None:
    server = build_server(sample_payload)
    response = server.handle_request(
        {
            "command": messages.COMMAND_MESSAGES_LIST,
            "params": {"limit": 0},
        }
    )
    assert "error" in response
    assert response["error"]["type"] == "ValueError"
