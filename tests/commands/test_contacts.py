import pytest

from fastmail_mcp.client import FastmailClient
from fastmail_mcp.commands import contacts
from fastmail_mcp.server import FastmailMCPServer


class DummyTransport:
    def list_contacts(self, *, limit: int):
        return [
            {
                "id": "c2",
                "name": "Grace Hopper",
                "emails": [{"value": "grace@example.com"}],
            },
            {
                "id": "c1",
                "name": "Ada Lovelace",
                "emails": [{"value": "ada@example.com"}],
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
    contacts.register(registry, client)
    return registry


def test_contacts_list_returns_sorted_results(server: FastmailMCPServer) -> None:
    response = server.handle_request(
        {
            "command": contacts.COMMAND_CONTACTS_LIST,
            "params": {"limit": 2},
        }
    )
    assert response["command"] == contacts.COMMAND_CONTACTS_LIST
    result = response["result"]
    assert result["count"] == 2
    names = [item["display_name"] for item in result["contacts"]]
    assert names == ["Ada Lovelace", "Grace Hopper"]


def test_contacts_invalid_limit(server: FastmailMCPServer) -> None:
    response = server.handle_request(
        {
            "command": contacts.COMMAND_CONTACTS_LIST,
            "params": {"limit": 0},
        }
    )
    assert response["error"]["type"] == "ValueError"
