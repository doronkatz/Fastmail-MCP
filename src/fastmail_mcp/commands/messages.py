"""Command registrations related to Fastmail messages."""

from __future__ import annotations

from functools import partial
from typing import Any, Dict

from fastmail_mcp.client import FastmailClient

COMMAND_MESSAGES_LIST = "messages-list"


def register(server: "FastmailMCPServer", client: FastmailClient) -> None:
    """Register message-centric commands with the MCP server."""

    server.register_command(
        COMMAND_MESSAGES_LIST,
        handler=partial(list_messages, client=client),
        description="Return recent Fastmail messages for the authenticated account.",
    )


def list_messages(*, client: FastmailClient, limit: int = 10) -> Dict[str, Any]:
    """Retrieve a trimmed payload of messages for the agent response."""

    if limit <= 0:
        raise ValueError("limit must be positive")
    messages = client.list_recent_messages(limit=limit)
    return {
        "messages": [message.to_summary() for message in messages],
        "count": len(messages),
    }
