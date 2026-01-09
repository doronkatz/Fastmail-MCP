"""HTTP transport for Fastmail's JMAP API."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence

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
            raise FastmailTransportError(f"Failed to obtain JMAP session: {exc}") from exc
        if response.status_code >= 400:
            raise FastmailTransportError(
                f"JMAP session discovery failed with status {response.status_code}"
            )
        session_data: Mapping[str, Any] = response.json()
        primary_accounts = session_data.get("primaryAccounts", {})
        api_url = session_data.get("apiUrl")
        if not isinstance(primary_accounts, dict) or not api_url:
            raise FastmailTransportError("Unable to locate JMAP account information in session")
        self._account_ids = {
            capability: str(account_id)
            for capability, account_id in primary_accounts.items()
            if isinstance(account_id, str)
        }
        if not self._account_ids:
            raise FastmailTransportError("No JMAP accounts available for current credentials")
        self._api_url = str(api_url)

    def _account_for(self, capability: str) -> str:
        self._ensure_session()
        assert self._account_ids is not None
        account_id = self._account_ids.get(capability)
        if not account_id:
            raise FastmailTransportError(f"Capability {capability} unavailable for this account")
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
            raise FastmailTransportError("Contact/get response missing from JMAP payload")
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
            raise FastmailTransportError("CalendarEvent/get response missing from JMAP payload")
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


def _find_method_response(
    responses: Sequence[Sequence[Any]], name: str
) -> Sequence[Any] | None:
    for response in responses:
        if response and response[0] == name:
            return response
    return None


MappingWithResponses = Dict[str, Any]
