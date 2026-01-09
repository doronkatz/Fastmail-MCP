"""Aggregate command registration helpers."""

from __future__ import annotations

from fastmail_mcp.client import FastmailClient

from . import contacts, events, messages

__all__ = ["register_all"]


def register_all(server: "FastmailMCPServer", client: FastmailClient) -> None:
    """Register every command collection with the provided server."""

    messages.register(server, client)
    contacts.register(server, client)
    events.register(server, client)
