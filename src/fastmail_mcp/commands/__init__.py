"""Aggregate command registration helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmail_mcp.client import FastmailClient

from . import contacts, events, messages

if TYPE_CHECKING:
    from fastmail_mcp.server import FastmailMCPServer

__all__ = ["register_all"]


def register_all(server: "FastmailMCPServer", client: FastmailClient) -> None:
    """Register every command collection with the provided server."""

    messages.register(server, client)
    contacts.register(server, client)
    events.register(server, client)
