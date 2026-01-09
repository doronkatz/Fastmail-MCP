"""Command registrations related to Fastmail calendar events."""

from __future__ import annotations

from functools import partial
from typing import Any, Dict

from fastmail_mcp.client import FastmailClient

COMMAND_EVENTS_LIST = "events-list"


def register(server: "FastmailMCPServer", client: FastmailClient) -> None:
    server.register_command(
        COMMAND_EVENTS_LIST,
        handler=partial(list_events, client=client),
        description="Return upcoming Fastmail calendar events for the account.",
    )


def list_events(*, client: FastmailClient, limit: int = 10) -> Dict[str, Any]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    events = client.list_upcoming_events(limit=limit)
    return {
        "events": [event.to_summary() for event in events],
        "count": len(events),
    }
