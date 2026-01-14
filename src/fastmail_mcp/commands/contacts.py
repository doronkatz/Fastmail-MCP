"""Command registrations related to Fastmail contacts."""

from __future__ import annotations

from functools import partial
from typing import Any, Dict, TYPE_CHECKING

from fastmail_mcp.client import FastmailClient

if TYPE_CHECKING:
    from fastmail_mcp.server import FastmailMCPServer

COMMAND_CONTACTS_LIST = "contacts-list"


def register(server: "FastmailMCPServer", client: FastmailClient) -> None:
    server.register_command(
        COMMAND_CONTACTS_LIST,
        handler=partial(list_contacts, client=client),
        description="Return recent Fastmail contacts for the account.",
    )


def list_contacts(*, client: FastmailClient, limit: int = 10) -> Dict[str, Any]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    contacts = client.list_recent_contacts(limit=limit)
    return {
        "contacts": [contact.to_summary() for contact in contacts],
        "count": len(contacts),
    }
