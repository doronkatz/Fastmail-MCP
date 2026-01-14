"""HTTP transport for Fastmail's JMAP API."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:  # pragma: no cover - import guarded for optional dependency
    from requests import RequestException
except ImportError:  # pragma: no cover - fallback when requests missing
    RequestException = Exception

logger = logging.getLogger(__name__)

JMAP_CORE_CAPABILITY = "urn:ietf:params:jmap:core"
JMAP_MAIL_CAPABILITY = "urn:ietf:params:jmap:mail"
JMAP_CONTACTS_CAPABILITY = "urn:ietf:params:jmap:contacts"
JMAP_CALENDAR_CAPABILITY = "urn:ietf:params:jmap:calendars"
DEFAULT_SESSION_PATH = "/.well-known/jmap"


class FastmailTransportError(RuntimeError):
    """Raised when the transport cannot complete a JMAP request."""

    def __init__(
        self,
        message: str,
        error_type: str = "TransportError",
        troubleshooting: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.troubleshooting = troubleshooting

    @classmethod
    def auth_error(cls, message: str) -> "FastmailTransportError":
        """Create authentication-specific transport error."""
        return cls(
            message=message,
            error_type="AuthenticationError",
            troubleshooting=(
                "Check FASTMAIL_USERNAME and FASTMAIL_APP_PASSWORD in .env. "
                "Ensure app password is valid and not expired."
            ),
        )

    @classmethod
    def capability_error(cls, capability: str) -> "FastmailTransportError":
        """Create capability-specific transport error."""
        return cls(
            message=f"JMAP capability '{capability}' not available",
            error_type="CapabilityError",
            troubleshooting=(
                "This account may not have access to the requested feature. "
                "Contact your Fastmail administrator or check account permissions."
            ),
        )

    @classmethod
    def network_error(cls, message: str) -> "FastmailTransportError":
        """Create network-specific transport error."""
        return cls(
            message=message,
            error_type="NetworkError",
            troubleshooting=(
                "Check internet connectivity and Fastmail service status. "
                "Verify FASTMAIL_BASE_URL is correct."
            ),
        )


@dataclass
class JMAPTransport:
    """Thin wrapper over the JMAP HTTP API for read-only scenarios."""

    base_url: str
    username: str
    app_password: str
    token: str | None = None
    session: Any | None = None

    _api_url: str | None = None
    _account_ids: Dict[str, str] | None = None

    def list_messages(self, *, limit: int) -> List[Dict[str, Any]]:
        body = self._build_email_query(limit=limit)
        response = self._post(body)
        return self._parse_messages(response)

    def search_messages(
        self,
        *,
        limit: int,
        offset: int = 0,
        filter_obj: Dict[str, Any] | None = None,
        sort_by: str = "receivedAt",
        sort_ascending: bool = False,
    ) -> Dict[str, Any]:
        """Search messages with advanced filtering and pagination."""
        body = self._build_email_search_query(
            limit=limit,
            offset=offset,
            filter_obj=filter_obj or {},
            sort_by=sort_by,
            sort_ascending=sort_ascending,
        )
        response = self._post(body)
        return self._parse_message_search_response(response)

    def get_message(self, *, message_id: str, properties: List[str]) -> Dict[str, Any]:
        """Get specific message by ID with requested properties."""
        body = self._build_message_get_query(
            message_id=message_id, properties=properties
        )
        response = self._post(body)
        return self._parse_message_get_response(response)

    def list_mailboxes(self, *, limit: int, offset: int = 0) -> Dict[str, Any]:
        """List mailboxes/folders with pagination."""
        body = self._build_mailbox_query(limit=limit, offset=offset)
        response = self._post(body)
        return self._parse_mailbox_response(response)

    def list_contacts(self, *, limit: int) -> List[Dict[str, Any]]:
        body = self._build_contact_query(limit=limit)
        response = self._post(body)
        return self._parse_contacts(response)

    def list_events(self, *, limit: int) -> List[Dict[str, Any]]:
        body = self._build_event_query(limit=limit)
        response = self._post(body)
        return self._parse_events(response)

    # Internal helpers -------------------------------------------------

    def _ensure_session(self) -> None:
        if self._api_url and self._account_ids:
            return
        try:
            response = self._get_session().get(
                f"{self.base_url.rstrip('/')}{DEFAULT_SESSION_PATH}",
                timeout=10,
                **self._auth_kwargs(),
            )
        except RequestException as exc:  # pragma: no cover - network failure
            raise FastmailTransportError.network_error(
                f"Failed to obtain JMAP session: {exc}"
            ) from exc
        if response.status_code == 401:
            raise FastmailTransportError.auth_error(
                f"Authentication failed (status {response.status_code}). Check credentials."
            )
        elif response.status_code >= 400:
            raise FastmailTransportError.network_error(
                f"JMAP session discovery failed with status {response.status_code}"
            )
        session_data: Mapping[str, Any] = response.json()
        primary_accounts = session_data.get("primaryAccounts", {})
        api_url = session_data.get("apiUrl")
        if not isinstance(primary_accounts, dict) or not api_url:
            raise FastmailTransportError(
                "Unable to locate JMAP account information in session"
            )
        self._account_ids = {
            capability: str(account_id)
            for capability, account_id in primary_accounts.items()
            if isinstance(account_id, str)
        }
        if not self._account_ids:
            raise FastmailTransportError(
                "No JMAP accounts available for current credentials"
            )
        self._api_url = str(api_url)

    def _account_for(self, capability: str) -> str:
        self._ensure_session()
        assert self._account_ids is not None
        account_id = self._account_ids.get(capability)
        if not account_id:
            raise FastmailTransportError.capability_error(capability)
        return account_id

    def _build_email_query(self, *, limit: int) -> Dict[str, Any]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        account_id = self._account_for(JMAP_MAIL_CAPABILITY)
        return {
            "using": [JMAP_CORE_CAPABILITY, JMAP_MAIL_CAPABILITY],
            "methodCalls": [
                [
                    "Email/query",
                    {
                        "accountId": account_id,
                        "limit": limit,
                        "sort": [
                            {
                                "property": "receivedAt",
                                "isAscending": False,
                            }
                        ],
                    },
                    "a",
                ],
                [
                    "Email/get",
                    {
                        "accountId": account_id,
                        "properties": ["id", "subject", "preview", "receivedAt"],
                        "#ids": {
                            "resultOf": "a",
                            "name": "Email/query",
                            "path": "/ids",
                        },
                    },
                    "b",
                ],
            ],
        }

    def _build_contact_query(self, *, limit: int) -> Dict[str, Any]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        account_id = self._account_for(JMAP_CONTACTS_CAPABILITY)
        return {
            "using": [JMAP_CORE_CAPABILITY, JMAP_CONTACTS_CAPABILITY],
            "methodCalls": [
                [
                    "Contact/query",
                    {
                        "accountId": account_id,
                        "limit": limit,
                        "sort": [
                            {
                                "property": "name",
                                "isAscending": True,
                            }
                        ],
                    },
                    "a",
                ],
                [
                    "Contact/get",
                    {
                        "accountId": account_id,
                        "properties": ["id", "name", "emails"],
                        "#ids": {
                            "resultOf": "a",
                            "name": "Contact/query",
                            "path": "/ids",
                        },
                    },
                    "b",
                ],
            ],
        }

    def _build_event_query(self, *, limit: int) -> Dict[str, Any]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        account_id = self._account_for(JMAP_CALENDAR_CAPABILITY)
        return {
            "using": [JMAP_CORE_CAPABILITY, JMAP_CALENDAR_CAPABILITY],
            "methodCalls": [
                [
                    "CalendarEvent/query",
                    {
                        "accountId": account_id,
                        "limit": limit,
                        "sort": [
                            {
                                "property": "start",
                                "isAscending": True,
                            }
                        ],
                    },
                    "a",
                ],
                [
                    "CalendarEvent/get",
                    {
                        "accountId": account_id,
                        "properties": ["id", "title", "start", "end"],
                        "#ids": {
                            "resultOf": "a",
                            "name": "CalendarEvent/query",
                            "path": "/ids",
                        },
                    },
                    "b",
                ],
            ],
        }

    def _build_email_search_query(
        self,
        *,
        limit: int,
        offset: int = 0,
        filter_obj: Dict[str, Any] | None = None,
        sort_by: str = "receivedAt",
        sort_ascending: bool = False,
    ) -> Dict[str, Any]:
        """Build advanced email search query with filtering and pagination."""
        if limit <= 0:
            raise ValueError("limit must be positive")

        account_id = self._account_for(JMAP_MAIL_CAPABILITY)

        query_params = {
            "accountId": account_id,
            "limit": limit,
            "position": offset,
            "sort": [
                {
                    "property": sort_by,
                    "isAscending": sort_ascending,
                }
            ],
        }

        if filter_obj:
            query_params["filter"] = filter_obj

        # Extended properties for search results
        properties = [
            "id",
            "subject",
            "preview",
            "receivedAt",
            "from",
            "to",
            "keywords",
            "hasAttachment",
            "mailboxIds",
        ]

        return {
            "using": [JMAP_CORE_CAPABILITY, JMAP_MAIL_CAPABILITY],
            "methodCalls": [
                [
                    "Email/query",
                    query_params,
                    "search",
                ],
                [
                    "Email/get",
                    {
                        "accountId": account_id,
                        "properties": properties,
                        "#ids": {
                            "resultOf": "search",
                            "name": "Email/query",
                            "path": "/ids",
                        },
                    },
                    "get",
                ],
            ],
        }

    def _build_message_get_query(
        self, *, message_id: str, properties: List[str]
    ) -> Dict[str, Any]:
        """Build query to get specific message by ID."""
        account_id = self._account_for(JMAP_MAIL_CAPABILITY)

        return {
            "using": [JMAP_CORE_CAPABILITY, JMAP_MAIL_CAPABILITY],
            "methodCalls": [
                [
                    "Email/get",
                    {
                        "accountId": account_id,
                        "ids": [message_id],
                        "properties": properties,
                    },
                    "get",
                ],
            ],
        }

    def _build_mailbox_query(self, *, limit: int, offset: int = 0) -> Dict[str, Any]:
        """Build query to list mailboxes with pagination."""
        if limit <= 0:
            raise ValueError("limit must be positive")

        account_id = self._account_for(JMAP_MAIL_CAPABILITY)

        return {
            "using": [JMAP_CORE_CAPABILITY, JMAP_MAIL_CAPABILITY],
            "methodCalls": [
                [
                    "Mailbox/query",
                    {
                        "accountId": account_id,
                        "limit": limit,
                        "position": offset,
                        "sort": [
                            {
                                "property": "name",
                                "isAscending": True,
                            }
                        ],
                    },
                    "query",
                ],
                [
                    "Mailbox/get",
                    {
                        "accountId": account_id,
                        "properties": [
                            "id",
                            "name",
                            "parentId",
                            "unreadEmails",
                            "totalEmails",
                        ],
                        "#ids": {
                            "resultOf": "query",
                            "name": "Mailbox/query",
                            "path": "/ids",
                        },
                    },
                    "get",
                ],
            ],
        }

    def _post(self, body: Dict[str, Any]) -> Dict[str, Any]:
        assert self._api_url is not None
        try:
            response = self._get_session().post(
                self._api_url,
                json=body,
                timeout=10,
                **self._auth_kwargs(),
            )
        except RequestException as exc:  # pragma: no cover - network failure
            raise FastmailTransportError(f"JMAP request failed: {exc}") from exc
        if response.status_code >= 400:
            raise FastmailTransportError(
                f"JMAP request failed with status {response.status_code}: {response.text}"
            )
        return response.json()

    def _get_session(self):
        if self.session is None:
            try:
                from requests import Session
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise FastmailTransportError(
                    "The 'requests' package is required for live Fastmail access."
                ) from exc
            self.session = Session()
        return self.session

    def _auth_kwargs(self) -> Dict[str, Any]:
        if self.token:
            return {"headers": {"Authorization": f"Bearer {self.token}"}}
        return {"auth": (self.username, self.app_password)}

    @staticmethod
    def _parse_messages(payload: MappingWithResponses) -> List[Dict[str, Any]]:
        method_responses = payload.get("methodResponses", [])
        email_get = _find_method_response(method_responses, "Email/get")
        if email_get is None:
            raise FastmailTransportError("Email/get response missing from JMAP payload")
        _, data, _ = email_get
        items = data.get("list", [])
        messages: List[Dict[str, Any]] = []
        for item in items:
            messages.append(
                {
                    "id": item.get("id"),
                    "subject": item.get("subject", ""),
                    "snippet": item.get("preview", ""),
                    "received_at": item.get("receivedAt"),
                }
            )
        return messages

    @staticmethod
    def _parse_contacts(payload: MappingWithResponses) -> List[Dict[str, Any]]:
        method_responses = payload.get("methodResponses", [])
        contact_get = _find_method_response(method_responses, "Contact/get")
        if contact_get is None:
            raise FastmailTransportError(
                "Contact/get response missing from JMAP payload"
            )
        _, data, _ = contact_get
        items = data.get("list", [])
        contacts: List[Dict[str, Any]] = []
        for item in items:
            contacts.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name", ""),
                    "emails": item.get("emails", []),
                }
            )
        return contacts

    @staticmethod
    def _parse_events(payload: MappingWithResponses) -> List[Dict[str, Any]]:
        method_responses = payload.get("methodResponses", [])
        event_get = _find_method_response(method_responses, "CalendarEvent/get")
        if event_get is None:
            raise FastmailTransportError(
                "CalendarEvent/get response missing from JMAP payload"
            )
        _, data, _ = event_get
        items = data.get("list", [])
        events: List[Dict[str, Any]] = []
        for item in items:
            events.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "start": item.get("start"),
                    "end": item.get("end"),
                }
            )
        return events

    @staticmethod
    def _parse_message_search_response(payload: MappingWithResponses) -> Dict[str, Any]:
        """Parse search response with pagination and extended message data."""
        method_responses = payload.get("methodResponses", [])

        # Get query result for pagination info
        query_response = _find_method_response(method_responses, "Email/query")
        if query_response is None:
            raise FastmailTransportError(
                "Email/query response missing from JMAP payload"
            )

        _, query_data, _ = query_response

        # Get message details
        email_get = _find_method_response(method_responses, "Email/get")
        if email_get is None:
            raise FastmailTransportError("Email/get response missing from JMAP payload")

        _, get_data, _ = email_get
        items = get_data.get("list", [])

        messages = []
        for item in items:
            # Extract sender from 'from' field
            sender_field = item.get("from", [])
            sender = sender_field[0].get("email", "") if sender_field else ""

            # Check if message is read (absence of \Unseen keyword)
            keywords = item.get("keywords", {})
            is_read = "$seen" in keywords or "\\Seen" in keywords

            # Get mailbox info
            mailbox_ids = item.get("mailboxIds", {})
            primary_mailbox = list(mailbox_ids.keys())[0] if mailbox_ids else None

            messages.append(
                {
                    "id": item.get("id"),
                    "subject": item.get("subject", ""),
                    "sender": sender,
                    "snippet": item.get("preview", ""),
                    "received_at": item.get("receivedAt"),
                    "read": is_read,
                    "has_attachment": item.get("hasAttachment", False),
                    "mailbox": primary_mailbox,
                }
            )

        return {
            "messages": messages,
            "total": query_data.get("total"),
            "position": query_data.get("position", 0),
            "limit": query_data.get("limit"),
            "can_calculate_changes": query_data.get("canCalculateChanges", False),
        }

    @staticmethod
    def _parse_message_get_response(payload: MappingWithResponses) -> Dict[str, Any]:
        """Parse get message response for detailed message data."""
        method_responses = payload.get("methodResponses", [])
        email_get = _find_method_response(method_responses, "Email/get")
        if email_get is None:
            raise FastmailTransportError("Email/get response missing from JMAP payload")

        _, data, _ = email_get
        items = data.get("list", [])

        if not items:
            raise FastmailTransportError("Message not found")

        item = items[0]  # Should only be one message for get by ID

        # Extract email addresses from address objects
        def extract_addresses(addr_list):
            return [addr.get("email", "") for addr in (addr_list or [])]

        sender_field = item.get("from", [])
        sender = sender_field[0].get("email", "") if sender_field else ""

        return {
            "id": item.get("id"),
            "subject": item.get("subject", ""),
            "sender": sender,
            "to": extract_addresses(item.get("to")),
            "cc": extract_addresses(item.get("cc")),
            "bcc": extract_addresses(item.get("bcc")),
            "received_at": item.get("receivedAt"),
            "sent_at": item.get("sentAt"),
            "body_text": item.get("textBody"),
            "body_html": item.get("htmlBody"),
            "headers": item.get("headers"),
            "attachments": item.get("attachments"),
        }

    @staticmethod
    def _parse_mailbox_response(payload: MappingWithResponses) -> Dict[str, Any]:
        """Parse mailbox list response with pagination."""
        method_responses = payload.get("methodResponses", [])

        # Get query result for pagination
        query_response = _find_method_response(method_responses, "Mailbox/query")
        if query_response is None:
            raise FastmailTransportError(
                "Mailbox/query response missing from JMAP payload"
            )

        _, query_data, _ = query_response

        # Get mailbox details
        mailbox_get = _find_method_response(method_responses, "Mailbox/get")
        if mailbox_get is None:
            raise FastmailTransportError(
                "Mailbox/get response missing from JMAP payload"
            )

        _, get_data, _ = mailbox_get
        items = get_data.get("list", [])

        mailboxes = []
        for item in items:
            mailboxes.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name", ""),
                    "parent_id": item.get("parentId"),
                    "unread_count": item.get("unreadEmails", 0),
                    "total_count": item.get("totalEmails", 0),
                }
            )

        return {
            "mailboxes": mailboxes,
            "total": query_data.get("total"),
            "position": query_data.get("position", 0),
            "limit": query_data.get("limit"),
        }


def _find_method_response(
    responses: Sequence[Sequence[Any]], name: str
) -> Sequence[Any] | None:
    for response in responses:
        if response and response[0] == name:
            return response
    return None


MappingWithResponses = Dict[str, Any]
