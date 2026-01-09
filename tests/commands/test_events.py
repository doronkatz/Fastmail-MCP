import pytest

from fastmail_mcp.client import FastmailClient
from fastmail_mcp.commands import events
from fastmail_mcp.server import FastmailMCPServer


class DummyTransport:
    def list_events(self, *, limit: int):
        return [
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


@pytest.fixture()
def server() -> FastmailMCPServer:
    client = FastmailClient(
        base_url="https://api.example.com",
        username="tester",
        app_password="secret",
        transport=DummyTransport(),
    )
    registry = FastmailMCPServer(client)
    events.register(registry, client)
    return registry


def test_events_list_returns_results(server: FastmailMCPServer) -> None:
    response = server.handle_request(
        {
            "command": events.COMMAND_EVENTS_LIST,
            "params": {"limit": 2},
        }
    )
    assert response["command"] == events.COMMAND_EVENTS_LIST
    result = response["result"]
    assert result["count"] == 2
    titles = [item["title"] for item in result["events"]]
    assert titles == ["Standup", "Retro"]


def test_events_invalid_limit(server: FastmailMCPServer) -> None:
    response = server.handle_request(
        {
            "command": events.COMMAND_EVENTS_LIST,
            "params": {"limit": 0},
        }
    )
    assert response["error"]["type"] == "ValueError"
