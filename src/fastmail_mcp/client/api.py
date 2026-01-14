"""Client abstraction for interacting with Fastmail's APIs or local fixtures."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, TYPE_CHECKING

from fastmail_mcp.models import CalendarEvent, Contact, Message
from fastmail_mcp.client.transport import FastmailTransportError, JMAPTransport

if TYPE_CHECKING:
    from fastmail_mcp.schemas import MailFilter, PaginationRequest

logger = logging.getLogger(__name__)


class FastmailClient:
    """Hybrid Fastmail client that prefers live JMAP data with fixture fallback."""

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        app_password: str,
        token: str | None = None,
        sample_path: Path | None = None,
        transport: JMAPTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.app_password = app_password
        self.token = token
        self._sample_messages_path = sample_path or self._default_messages_path()
        self._sample_contacts_path = self._default_contacts_path()
        self._sample_events_path = self._default_events_path()
        self._transport = transport or JMAPTransport(
            base_url=self.base_url,
            username=username,
            app_password=app_password,
            token=token or None,
        )

    def list_recent_messages(self, *, limit: int = 10) -> List[Message]:
        """Return recent messages, preferring live JMAP data and falling back to fixtures."""

        messages: Sequence[Message]
        try:
            live_payload = self._transport.list_messages(limit=limit)
        except FastmailTransportError as exc:
            logger.warning("Falling back to fixture messages: %s", exc)
            messages = self._load_sample_messages()
        else:
            try:
                messages = [Message.from_json(item) for item in live_payload]
            except (ValueError, KeyError) as exc:
                logger.warning("Invalid live payload, using fixtures: %s", exc)
                messages = self._load_sample_messages()

        messages = sorted(messages, key=lambda msg: msg.received_at, reverse=True)
        return list(messages[:limit])

    def list_recent_contacts(self, *, limit: int = 10) -> List[Contact]:
        contacts: Sequence[Contact]
        try:
            live_payload = self._transport.list_contacts(limit=limit)
        except FastmailTransportError as exc:
            logger.warning("Falling back to fixture contacts: %s", exc)
            contacts = self._load_sample_contacts()
        else:
            try:
                contacts = [Contact.from_json(item) for item in live_payload]
            except (ValueError, KeyError) as exc:
                logger.warning("Invalid live contact payload, using fixtures: %s", exc)
                contacts = self._load_sample_contacts()

        contacts = sorted(contacts, key=lambda contact: contact.display_name)
        return list(contacts[:limit])

    def list_upcoming_events(self, *, limit: int = 10) -> List[CalendarEvent]:
        events: Sequence[CalendarEvent]
        try:
            live_payload = self._transport.list_events(limit=limit)
        except FastmailTransportError as exc:
            logger.warning("Falling back to fixture events: %s", exc)
            events = self._load_sample_events()
        else:
            try:
                events = [CalendarEvent.from_json(item) for item in live_payload]
            except (ValueError, KeyError) as exc:
                logger.warning("Invalid live event payload, using fixtures: %s", exc)
                events = self._load_sample_events()

        events = sorted(events, key=lambda event: event.starts_at)
        return list(events[:limit])

    def search_messages(
        self,
        *,
        filter_obj: Optional["MailFilter"] = None,
        pagination: Optional["PaginationRequest"] = None,
        sort_by: str = "receivedAt",
        sort_ascending: bool = False,
    ) -> Dict[str, Any]:
        """Search messages with advanced filtering and pagination."""

        if pagination is None:
            from fastmail_mcp.schemas import PaginationRequest

            pagination = PaginationRequest()

        try:
            # Convert filter to JMAP format if provided
            jmap_filter = None
            if filter_obj:
                jmap_filter = filter_obj.to_jmap_filter()

            result = self._transport.search_messages(
                limit=pagination.limit,
                offset=pagination.offset,
                filter_obj=jmap_filter,
                sort_by=sort_by,
                sort_ascending=sort_ascending,
            )
            return result

        except FastmailTransportError as exc:
            logger.warning("Search failed, using fixture fallback: %s", exc)
            # Fallback to basic message list for search failures
            messages = self.list_recent_messages(limit=pagination.limit)
            return {
                "messages": [msg.to_summary() for msg in messages],
                "total": len(messages),
                "position": pagination.offset,
                "limit": pagination.limit,
            }

    def get_message(self, *, message_id: str, properties: List[str]) -> Dict[str, Any]:
        """Get specific message by ID with requested properties."""

        try:
            result = self._transport.get_message(
                message_id=message_id,
                properties=properties,
            )
            return result

        except FastmailTransportError as exc:
            logger.warning("Get message failed: %s", exc)
            # For get operations, we can't provide meaningful fallback
            raise exc

    def list_mailboxes(self, *, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """List mailboxes with pagination."""

        try:
            result = self._transport.list_mailboxes(
                limit=limit,
                offset=offset,
            )
            return result

        except FastmailTransportError as exc:
            logger.warning("List mailboxes failed: %s", exc)
            # Provide basic fallback structure
            return {
                "mailboxes": [
                    {
                        "id": "inbox",
                        "name": "Inbox",
                        "parent_id": None,
                        "unread_count": 0,
                        "total_count": 0,
                    }
                ],
                "total": 1,
                "position": offset,
                "limit": limit,
            }

    def _sample_payload(self) -> Iterable[dict]:
        path = self._sample_messages_path
        if not path.exists():
            raise FileNotFoundError(
                f"Sample data missing at {path}. Provide FASTMAIL_SAMPLE_DATA or a live transport."
            )
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise ValueError("Sample message payload must be a list")
        return payload

    def _load_sample_messages(self) -> List[Message]:
        return [Message.from_json(item) for item in self._sample_payload()]

    def _load_sample_contacts(self) -> List[Contact]:
        payload = self._read_sample_file(self._sample_contacts_path)
        return [Contact.from_json(item) for item in payload]

    def _load_sample_events(self) -> List[CalendarEvent]:
        payload = self._read_sample_file(self._sample_events_path)
        return [CalendarEvent.from_json(item) for item in payload]

    @staticmethod
    def _read_sample_file(path: Path) -> List[dict]:
        if not path.exists():
            raise FileNotFoundError(f"Sample data missing at {path}")
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise ValueError(f"Sample payload at {path} must be a list")
        return payload

    @staticmethod
    def _default_messages_path() -> Path:
        env_override = os.environ.get("FASTMAIL_SAMPLE_DATA")
        if env_override:
            return Path(env_override)
        return Path("assets/messages_sample.json")

    @staticmethod
    def _default_contacts_path() -> Path:
        env_override = os.environ.get("FASTMAIL_CONTACT_SAMPLE_DATA")
        if env_override:
            return Path(env_override)
        return Path("assets/contacts_sample.json")

    @staticmethod
    def _default_events_path() -> Path:
        env_override = os.environ.get("FASTMAIL_EVENT_SAMPLE_DATA")
        if env_override:
            return Path(env_override)
        return Path("assets/events_sample.json")
