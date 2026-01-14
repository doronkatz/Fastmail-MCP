"""Mail-specific schema definitions for MCP tools."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import PaginationRequest, PaginationResponse


@dataclass
class DateRange:
    """Date range filter for mail queries."""

    start: Optional[datetime] = None
    end: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.start and self.end and self.start > self.end:
            raise ValueError("start date cannot be after end date")

    @classmethod
    def from_strings(cls, start: Optional[str], end: Optional[str]) -> "DateRange":
        """Create DateRange from ISO format strings."""
        start_dt = None
        end_dt = None

        if start:
            try:
                start_dt = datetime.fromisoformat(start)
            except ValueError as e:
                raise ValueError(f"Invalid start date format: {e}")

        if end:
            try:
                end_dt = datetime.fromisoformat(end)
            except ValueError as e:
                raise ValueError(f"Invalid end date format: {e}")

        return cls(start=start_dt, end=end_dt)


@dataclass
class MailFilter:
    """Comprehensive filter options for mail queries."""

    sender: Optional[str] = None
    subject: Optional[str] = None
    mailbox: Optional[str] = None
    read: Optional[bool] = None
    date_range: Optional[DateRange] = None
    has_attachment: Optional[bool] = None

    def to_jmap_filter(self) -> Dict[str, Any]:
        """Convert to JMAP filter object."""
        jmap_filter = {}

        if self.sender:
            jmap_filter["from"] = self.sender

        if self.subject:
            jmap_filter["subject"] = self.subject

        if self.mailbox:
            jmap_filter["inMailbox"] = self.mailbox

        if self.read is not None:
            jmap_filter["isUnread"] = not self.read

        if self.has_attachment is not None:
            jmap_filter["hasAttachment"] = self.has_attachment

        if self.date_range:
            if self.date_range.start:
                jmap_filter["after"] = self.date_range.start.isoformat()
            if self.date_range.end:
                jmap_filter["before"] = self.date_range.end.isoformat()

        return jmap_filter


# Request schemas


@dataclass
class MessageSearchRequest:
    """Request schema for searching messages with filters."""

    filter: Optional[MailFilter] = None
    pagination: Optional[PaginationRequest] = None
    sort_by: str = "receivedAt"
    sort_ascending: bool = False

    def __post_init__(self) -> None:
        if self.pagination is None:
            self.pagination = PaginationRequest()

        valid_sort_fields = {"receivedAt", "sentAt", "subject", "from"}
        if self.sort_by not in valid_sort_fields:
            raise ValueError(f"sort_by must be one of: {valid_sort_fields}")


@dataclass
class MessageGetRequest:
    """Request schema for getting specific message by ID."""

    message_id: str
    include_body: bool = False
    include_headers: bool = False

    def __post_init__(self) -> None:
        if not self.message_id:
            raise ValueError("message_id is required")


@dataclass
class MailboxListRequest:
    """Request schema for listing mailboxes."""

    pagination: Optional[PaginationRequest] = None

    def __post_init__(self) -> None:
        if self.pagination is None:
            self.pagination = PaginationRequest()


@dataclass
class MessageSendRequest:
    """Request schema for sending email messages."""

    to: List[str]
    subject: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if not self.to:
            raise ValueError("to field is required")
        if not self.subject:
            raise ValueError("subject is required")
        if not self.body_text and not self.body_html:
            raise ValueError("either body_text or body_html is required")


# Response schemas


@dataclass
class MessageSummary:
    """Summary representation of a message for list responses."""

    id: str
    subject: str
    sender: str
    snippet: str
    received_at: datetime
    read: bool = False
    has_attachment: bool = False
    mailbox: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "subject": self.subject,
            "sender": self.sender,
            "snippet": self.snippet,
            "received_at": self.received_at.isoformat(),
            "read": self.read,
            "has_attachment": self.has_attachment,
            "mailbox": self.mailbox,
        }


@dataclass
class MessageDetail:
    """Detailed representation of a message for get responses."""

    id: str
    subject: str
    sender: str
    to: List[str]
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    received_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    attachments: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "subject": self.subject,
            "sender": self.sender,
            "to": self.to,
        }

        if self.cc:
            result["cc"] = self.cc
        if self.bcc:
            result["bcc"] = self.bcc
        if self.received_at:
            result["received_at"] = self.received_at.isoformat()
        if self.sent_at:
            result["sent_at"] = self.sent_at.isoformat()
        if self.body_text:
            result["body_text"] = self.body_text
        if self.body_html:
            result["body_html"] = self.body_html
        if self.headers:
            result["headers"] = self.headers
        if self.attachments:
            result["attachments"] = self.attachments

        return result


@dataclass
class MailboxInfo:
    """Information about a mailbox/folder."""

    id: str
    name: str
    parent_id: Optional[str] = None
    unread_count: int = 0
    total_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "unread_count": self.unread_count,
            "total_count": self.total_count,
        }


@dataclass
class MessageSearchResponse:
    """Response schema for message search results."""

    messages: List[MessageSummary]
    pagination: PaginationResponse

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "messages": [msg.to_dict() for msg in self.messages],
            "pagination": {
                "limit": self.pagination.limit,
                "offset": self.pagination.offset,
                "total": self.pagination.total,
                "has_more": self.pagination.has_more,
            },
        }


@dataclass
class MessageGetResponse:
    """Response schema for getting a specific message."""

    message: MessageDetail

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"message": self.message.to_dict()}


@dataclass
class MailboxListResponse:
    """Response schema for listing mailboxes."""

    mailboxes: List[MailboxInfo]
    pagination: PaginationResponse

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "mailboxes": [mb.to_dict() for mb in self.mailboxes],
            "pagination": {
                "limit": self.pagination.limit,
                "offset": self.pagination.offset,
                "total": self.pagination.total,
                "has_more": self.pagination.has_more,
            },
        }


@dataclass
class MessageSendResponse:
    """Response schema for sending messages."""

    message_id: str
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "message_id": self.message_id,
            "success": self.success,
        }
