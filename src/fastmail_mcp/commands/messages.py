"""Command registrations related to Fastmail messages."""

from __future__ import annotations

import os
from datetime import datetime
from functools import partial
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from fastmail_mcp.client import FastmailClient

if TYPE_CHECKING:
    from fastmail_mcp.server import FastmailMCPServer
from fastmail_mcp.schemas import (
    MailFilter,
    DateRange,
    MessageSearchRequest,
    MessageGetRequest,
    MailboxListRequest,
    MessageSendRequest,
    MessageSearchResponse,
    MessageGetResponse,
    MailboxListResponse,
    MessageSendResponse,
    MessageSummary,
    MessageDetail,
    MailboxInfo,
    PaginationRequest,
    PaginationResponse,
    ErrorResponse,
)

# Command identifiers
COMMAND_MESSAGES_LIST = "messages-list"
COMMAND_MESSAGES_SEARCH = "messages-search"
COMMAND_MESSAGES_GET = "messages-get"
COMMAND_MAILBOXES_LIST = "mailboxes-list"
COMMAND_MESSAGES_SEND = "messages-send"


def register(server: "FastmailMCPServer", client: FastmailClient) -> None:
    """Register message-centric commands with the MCP server."""

    # Legacy list command for backward compatibility
    server.register_command(
        COMMAND_MESSAGES_LIST,
        handler=partial(list_messages, client=client),
        description="Return recent Fastmail messages for the authenticated account.",
    )

    # Enhanced search command with filtering
    server.register_command(
        COMMAND_MESSAGES_SEARCH,
        handler=partial(search_messages, client=client),
        description=(
            "Search Fastmail messages with advanced filtering options. "
            "Supports filtering by sender, subject, date ranges, mailbox, read status, and attachments."
        ),
    )

    # Get specific message by ID
    server.register_command(
        COMMAND_MESSAGES_GET,
        handler=partial(get_message, client=client),
        description="Get detailed information for a specific message by ID.",
    )

    # List mailboxes/folders
    server.register_command(
        COMMAND_MAILBOXES_LIST,
        handler=partial(list_mailboxes, client=client),
        description="List available mailboxes/folders with unread and total counts.",
    )

    # Send message (write operation, gated by environment variable)
    if _is_write_enabled():
        server.register_command(
            COMMAND_MESSAGES_SEND,
            handler=partial(send_message, client=client),
            description="[WRITE] Send an email message. Requires FASTMAIL_ENABLE_WRITE_TOOLS=true.",
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


def search_messages(
    *,
    client: FastmailClient,
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    mailbox: Optional[str] = None,
    read: Optional[bool] = None,
    has_attachment: Optional[bool] = None,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    sort_by: str = "receivedAt",
    sort_ascending: bool = False,
) -> Dict[str, Any]:
    """Search messages with advanced filtering and pagination."""

    try:
        # Build filter from parameters
        date_range = None
        if date_start or date_end:
            date_range = DateRange.from_strings(date_start, date_end)

        mail_filter = MailFilter(
            sender=sender,
            subject=subject,
            mailbox=mailbox,
            read=read,
            has_attachment=has_attachment,
            date_range=date_range,
        )

        # Create request object
        request = MessageSearchRequest(
            filter=mail_filter,
            pagination=PaginationRequest(limit=limit, offset=offset),
            sort_by=sort_by,
            sort_ascending=sort_ascending,
        )

        # Execute search
        result = client.search_messages(
            filter_obj=request.filter,
            pagination=request.pagination,
            sort_by=request.sort_by,
            sort_ascending=request.sort_ascending,
        )

        # Convert to response schema
        messages = [_dict_to_message_summary(msg) for msg in result["messages"]]
        pagination = PaginationResponse(
            limit=result.get("limit", limit),
            offset=result.get("position", offset),
            total=result.get("total"),
            has_more=result.get("position", 0) + len(messages) < result.get("total", 0),
        )

        response = MessageSearchResponse(messages=messages, pagination=pagination)
        return response.to_dict()

    except ValueError as e:
        error = ErrorResponse.validation_error("search parameters", str(e))
        return {"error": error.__dict__}
    except Exception as e:
        error = ErrorResponse.network_error(f"Search failed: {str(e)}")
        return {"error": error.__dict__}


def get_message(
    *,
    client: FastmailClient,
    message_id: str,
    include_body: bool = False,
    include_headers: bool = False,
) -> Dict[str, Any]:
    """Get detailed message information by ID."""

    try:
        MessageGetRequest(
            message_id=message_id,
            include_body=include_body,
            include_headers=include_headers,
        )

        # Determine which properties to request
        properties = [
            "id",
            "subject",
            "from",
            "to",
            "cc",
            "bcc",
            "receivedAt",
            "sentAt",
        ]
        if include_body:
            properties.extend(["textBody", "htmlBody", "attachments"])
        if include_headers:
            properties.append("headers")

        result = client.get_message(message_id=message_id, properties=properties)

        # Convert to response schema
        message = _dict_to_message_detail(result)
        response = MessageGetResponse(message=message)
        return response.to_dict()

    except ValueError as e:
        error = ErrorResponse.validation_error("message_id", str(e))
        return {"error": error.__dict__}
    except Exception as e:
        error = ErrorResponse.network_error(f"Failed to get message: {str(e)}")
        return {"error": error.__dict__}


def list_mailboxes(
    *,
    client: FastmailClient,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List mailboxes/folders with pagination."""

    try:
        request = MailboxListRequest(
            pagination=PaginationRequest(limit=limit, offset=offset)
        )

        result = client.list_mailboxes(
            limit=request.pagination.limit,
            offset=request.pagination.offset,
        )

        # Convert to response schema
        mailboxes = [_dict_to_mailbox_info(mb) for mb in result["mailboxes"]]
        pagination = PaginationResponse(
            limit=result.get("limit", limit),
            offset=result.get("position", offset),
            total=result.get("total"),
            has_more=result.get("position", 0) + len(mailboxes)
            < result.get("total", 0),
        )

        response = MailboxListResponse(mailboxes=mailboxes, pagination=pagination)
        return response.to_dict()

    except Exception as e:
        error = ErrorResponse.network_error(f"Failed to list mailboxes: {str(e)}")
        return {"error": error.__dict__}


def send_message(
    *,
    client: FastmailClient,
    to: List[str],
    subject: str,
    body_text: Optional[str] = None,
    body_html: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Send an email message (write operation)."""

    if not _is_write_enabled():
        error = ErrorResponse(
            error_type="PermissionDenied",
            message="Write operations are disabled",
            troubleshooting="Set FASTMAIL_ENABLE_WRITE_TOOLS=true to enable message sending",
        )
        return {"error": error.__dict__}

    try:
        MessageSendRequest(
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
        )

        # For now, return a placeholder response since JMAP submission
        # requires additional implementation
        # TODO: Implement actual email sending via JMAP EmailSubmission

        response = MessageSendResponse(
            message_id="placeholder-id",
            success=False,  # Not yet implemented
        )

        # Add note about implementation status
        result = response.to_dict()
        result["note"] = "Email sending not yet implemented. Placeholder response only."
        return result

    except ValueError as e:
        error = ErrorResponse.validation_error("send parameters", str(e))
        return {"error": error.__dict__}
    except Exception as e:
        error = ErrorResponse.network_error(f"Failed to send message: {str(e)}")
        return {"error": error.__dict__}


# Helper functions


def _is_write_enabled() -> bool:
    """Check if write operations are enabled via environment variable."""
    return os.environ.get("FASTMAIL_ENABLE_WRITE_TOOLS", "").lower() == "true"


def _dict_to_message_summary(data: Dict[str, Any]) -> MessageSummary:
    """Convert transport dictionary to MessageSummary schema."""
    received_at = data.get("received_at")
    if isinstance(received_at, str):
        received_at = datetime.fromisoformat(received_at)

    return MessageSummary(
        id=data["id"],
        subject=data.get("subject", ""),
        sender=data.get("sender", ""),
        snippet=data.get("snippet", ""),
        received_at=received_at,
        read=data.get("read", False),
        has_attachment=data.get("has_attachment", False),
        mailbox=data.get("mailbox"),
    )


def _dict_to_message_detail(data: Dict[str, Any]) -> MessageDetail:
    """Convert transport dictionary to MessageDetail schema."""
    received_at = data.get("received_at")
    if isinstance(received_at, str):
        received_at = datetime.fromisoformat(received_at)

    sent_at = data.get("sent_at")
    if isinstance(sent_at, str):
        sent_at = datetime.fromisoformat(sent_at)

    return MessageDetail(
        id=data["id"],
        subject=data.get("subject", ""),
        sender=data.get("sender", ""),
        to=data.get("to", []),
        cc=data.get("cc"),
        bcc=data.get("bcc"),
        received_at=received_at,
        sent_at=sent_at,
        body_text=data.get("body_text"),
        body_html=data.get("body_html"),
        headers=data.get("headers"),
        attachments=data.get("attachments"),
    )


def _dict_to_mailbox_info(data: Dict[str, Any]) -> MailboxInfo:
    """Convert transport dictionary to MailboxInfo schema."""
    return MailboxInfo(
        id=data["id"],
        name=data.get("name", ""),
        parent_id=data.get("parent_id"),
        unread_count=data.get("unread_count", 0),
        total_count=data.get("total_count", 0),
    )
