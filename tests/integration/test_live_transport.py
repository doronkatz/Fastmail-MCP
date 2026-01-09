import os

import pytest

from fastmail_mcp.client.transport import FastmailTransportError
from fastmail_mcp.server import build_client
from fastmail_mcp.utils import load_env

pytestmark = pytest.mark.slow


@pytest.mark.skipif(
    not os.environ.get("FASTMAIL_LIVE_TESTS"),
    reason="FASTMAIL_LIVE_TESTS not enabled",
)
def test_live_messages_roundtrip():
    load_env()
    client = build_client()
    try:
        messages = client.list_recent_messages(limit=1)
    except FastmailTransportError as exc:
        pytest.skip(f"Live transport unavailable: {exc}")
    assert isinstance(messages, list)
