"""Schema definitions for MCP tool inputs and outputs."""

from .base import PaginationRequest, PaginationResponse, ErrorResponse
from .mail import (
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
)

__all__ = [
    # Base schemas
    "PaginationRequest",
    "PaginationResponse",
    "ErrorResponse",
    # Mail schemas
    "MailFilter",
    "DateRange",
    "MessageSearchRequest",
    "MessageGetRequest",
    "MailboxListRequest",
    "MessageSendRequest",
    "MessageSearchResponse",
    "MessageGetResponse",
    "MailboxListResponse",
    "MessageSendResponse",
    "MessageSummary",
    "MessageDetail",
    "MailboxInfo",
]
