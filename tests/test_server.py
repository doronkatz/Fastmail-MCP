import io
import json

from fastmail_mcp.client import FastmailClient
from fastmail_mcp.commands import messages
from fastmail_mcp.server import FastmailMCPServer


class _NullTransport:
    def list_messages(self, *, limit: int):  # pragma: no cover - used only in tests
        return []

    def list_contacts(self, *, limit: int):  # pragma: no cover - used only in tests
        return []

    def list_events(self, *, limit: int):  # pragma: no cover - used only in tests
        return []


class DummyClient(FastmailClient):
    def __init__(self) -> None:
        super().__init__(
            base_url="https://api.example.com",
            username="dummy",
            app_password="dummy",
            sample_path=None,
            transport=_NullTransport(),
        )
        self._messages = []

    def list_recent_messages(self, *, limit: int = 10):
        return self._messages[:limit]


def test_unknown_command_returns_error() -> None:
    client = DummyClient()
    server = FastmailMCPServer(client)

    response = server.handle_request({"command": "missing"})

    assert response["error"]["type"] == "KeyError"


def test_serve_forever_writes_responses() -> None:
    client = DummyClient()
    client._messages = []
    server = FastmailMCPServer(client)
    messages.register(server, client)

    request = {"command": messages.COMMAND_MESSAGES_LIST, "params": {"limit": 1}}
    input_stream = io.StringIO(json.dumps(request) + "\n")
    output_stream = io.StringIO()

    server.serve_forever(input_stream=input_stream, output_stream=output_stream)

    output_stream.seek(0)
    response = json.loads(output_stream.readline())
    assert response["command"] == messages.COMMAND_MESSAGES_LIST
    assert response["result"]["messages"] == []
