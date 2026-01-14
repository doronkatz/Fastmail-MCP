"""Tests for MCP schemas and validation."""

import pytest
from datetime import datetime

from fastmail_mcp.schemas import (
    PaginationRequest,
    ErrorResponse,
    DateRange,
    MailFilter,
    MessageSearchRequest,
    MessageGetRequest,
    MessageSendRequest,
    MessageSummary,
    MessageDetail,
)


class TestPaginationRequest:
    def test_valid_pagination(self):
        """Test valid pagination parameters."""
        pagination = PaginationRequest(limit=50, offset=10)
        assert pagination.limit == 50
        assert pagination.offset == 10

    def test_default_values(self):
        """Test default pagination values."""
        pagination = PaginationRequest()
        assert pagination.limit == 10
        assert pagination.offset == 0

    def test_invalid_limit_zero(self):
        """Test validation for zero limit."""
        with pytest.raises(ValueError, match="limit must be positive"):
            PaginationRequest(limit=0)

    def test_invalid_limit_negative(self):
        """Test validation for negative limit."""
        with pytest.raises(ValueError, match="limit must be positive"):
            PaginationRequest(limit=-1)

    def test_invalid_offset_negative(self):
        """Test validation for negative offset."""
        with pytest.raises(ValueError, match="offset must be non-negative"):
            PaginationRequest(offset=-1)

    def test_limit_too_large(self):
        """Test validation for limit exceeding maximum."""
        with pytest.raises(ValueError, match="limit cannot exceed 100"):
            PaginationRequest(limit=150)


class TestDateRange:
    def test_valid_date_range(self):
        """Test valid date range creation."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        date_range = DateRange(start=start, end=end)
        assert date_range.start == start
        assert date_range.end == end

    def test_invalid_date_range_order(self):
        """Test validation for invalid date order."""
        start = datetime(2024, 1, 31)
        end = datetime(2024, 1, 1)
        with pytest.raises(ValueError, match="start date cannot be after end date"):
            DateRange(start=start, end=end)

    def test_from_strings_valid(self):
        """Test creation from valid ISO strings."""
        date_range = DateRange.from_strings(
            "2024-01-01T00:00:00Z", "2024-01-31T23:59:59Z"
        )
        assert date_range.start.year == 2024
        assert date_range.start.month == 1
        assert date_range.start.day == 1
        assert date_range.end.year == 2024
        assert date_range.end.month == 1
        assert date_range.end.day == 31

    def test_from_strings_invalid_start(self):
        """Test error handling for invalid start date string."""
        with pytest.raises(ValueError, match="Invalid start date format"):
            DateRange.from_strings("invalid-date", "2024-01-31T00:00:00Z")

    def test_from_strings_invalid_end(self):
        """Test error handling for invalid end date string."""
        with pytest.raises(ValueError, match="Invalid end date format"):
            DateRange.from_strings("2024-01-01T00:00:00Z", "invalid-date")

    def test_from_strings_none_values(self):
        """Test creation with None values."""
        date_range = DateRange.from_strings(None, None)
        assert date_range.start is None
        assert date_range.end is None


class TestMailFilter:
    def test_empty_filter_to_jmap(self):
        """Test empty filter conversion to JMAP."""
        mail_filter = MailFilter()
        jmap_filter = mail_filter.to_jmap_filter()
        assert jmap_filter == {}

    def test_sender_filter_to_jmap(self):
        """Test sender filter conversion to JMAP."""
        mail_filter = MailFilter(sender="test@example.com")
        jmap_filter = mail_filter.to_jmap_filter()
        assert jmap_filter["from"] == "test@example.com"

    def test_read_filter_to_jmap(self):
        """Test read status filter conversion to JMAP."""
        # Test read=True -> isUnread=False
        mail_filter = MailFilter(read=True)
        jmap_filter = mail_filter.to_jmap_filter()
        assert jmap_filter["isUnread"] is False

        # Test read=False -> isUnread=True
        mail_filter = MailFilter(read=False)
        jmap_filter = mail_filter.to_jmap_filter()
        assert jmap_filter["isUnread"] is True

    def test_date_range_filter_to_jmap(self):
        """Test date range filter conversion to JMAP."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        date_range = DateRange(start=start, end=end)
        mail_filter = MailFilter(date_range=date_range)
        jmap_filter = mail_filter.to_jmap_filter()

        assert jmap_filter["after"] == start.isoformat()
        assert jmap_filter["before"] == end.isoformat()

    def test_complex_filter_to_jmap(self):
        """Test complex filter with multiple criteria."""
        date_range = DateRange(start=datetime(2024, 1, 1))
        mail_filter = MailFilter(
            sender="test@example.com",
            subject="Important",
            read=False,
            has_attachment=True,
            date_range=date_range,
        )
        jmap_filter = mail_filter.to_jmap_filter()

        assert jmap_filter["from"] == "test@example.com"
        assert jmap_filter["subject"] == "Important"
        assert jmap_filter["isUnread"] is True
        assert jmap_filter["hasAttachment"] is True
        assert jmap_filter["after"] == "2024-01-01T00:00:00"


class TestMessageSearchRequest:
    def test_valid_request(self):
        """Test valid message search request."""
        request = MessageSearchRequest(sort_by="receivedAt", sort_ascending=False)
        assert request.sort_by == "receivedAt"
        assert request.sort_ascending is False
        assert request.pagination.limit == 10  # Default

    def test_invalid_sort_field(self):
        """Test validation for invalid sort field."""
        with pytest.raises(ValueError, match="sort_by must be one of"):
            MessageSearchRequest(sort_by="invalid_field")

    def test_default_pagination(self):
        """Test default pagination is created."""
        request = MessageSearchRequest()
        assert request.pagination is not None
        assert request.pagination.limit == 10


class TestMessageGetRequest:
    def test_valid_request(self):
        """Test valid message get request."""
        request = MessageGetRequest(
            message_id="msg123", include_body=True, include_headers=True
        )
        assert request.message_id == "msg123"
        assert request.include_body is True
        assert request.include_headers is True

    def test_empty_message_id(self):
        """Test validation for empty message ID."""
        with pytest.raises(ValueError, match="message_id is required"):
            MessageGetRequest(message_id="")


class TestMessageSendRequest:
    def test_valid_request(self):
        """Test valid message send request."""
        request = MessageSendRequest(
            to=["recipient@example.com"], subject="Test", body_text="Hello world"
        )
        assert request.to == ["recipient@example.com"]
        assert request.subject == "Test"
        assert request.body_text == "Hello world"

    def test_empty_to_field(self):
        """Test validation for empty to field."""
        with pytest.raises(ValueError, match="to field is required"):
            MessageSendRequest(to=[], subject="Test", body_text="Hello")

    def test_empty_subject(self):
        """Test validation for empty subject."""
        with pytest.raises(ValueError, match="subject is required"):
            MessageSendRequest(to=["test@example.com"], subject="", body_text="Hello")

    def test_no_body(self):
        """Test validation for missing body content."""
        with pytest.raises(
            ValueError, match="either body_text or body_html is required"
        ):
            MessageSendRequest(to=["test@example.com"], subject="Test")


class TestErrorResponse:
    def test_auth_error(self):
        """Test authentication error creation."""
        error = ErrorResponse.auth_error("Invalid credentials")
        assert error.error_type == "AuthenticationError"
        assert error.message == "Invalid credentials"
        assert "FASTMAIL_USERNAME" in error.troubleshooting

    def test_capability_error(self):
        """Test capability error creation."""
        error = ErrorResponse.capability_error("urn:ietf:params:jmap:mail")
        assert error.error_type == "CapabilityError"
        assert "urn:ietf:params:jmap:mail" in error.message
        assert "account permissions" in error.troubleshooting

    def test_network_error(self):
        """Test network error creation."""
        error = ErrorResponse.network_error("Connection failed")
        assert error.error_type == "NetworkError"
        assert error.message == "Connection failed"
        assert "connectivity" in error.troubleshooting

    def test_validation_error(self):
        """Test validation error creation."""
        error = ErrorResponse.validation_error("limit", "must be positive")
        assert error.error_type == "ValidationError"
        assert error.message == "Invalid limit: must be positive"
        assert error.details["field"] == "limit"


class TestMessageSummary:
    def test_to_dict(self):
        """Test message summary serialization."""
        received_at = datetime(2024, 1, 1, 12, 0, 0)
        message = MessageSummary(
            id="msg123",
            subject="Test",
            sender="test@example.com",
            snippet="Hello world",
            received_at=received_at,
            read=True,
            has_attachment=False,
            mailbox="inbox",
        )

        result = message.to_dict()
        assert result["id"] == "msg123"
        assert result["subject"] == "Test"
        assert result["sender"] == "test@example.com"
        assert result["received_at"] == "2024-01-01T12:00:00"
        assert result["read"] is True
        assert result["has_attachment"] is False
        assert result["mailbox"] == "inbox"


class TestMessageDetail:
    def test_to_dict_minimal(self):
        """Test minimal message detail serialization."""
        message = MessageDetail(
            id="msg123",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
        )

        result = message.to_dict()
        assert result["id"] == "msg123"
        assert result["subject"] == "Test"
        assert result["sender"] == "test@example.com"
        assert result["to"] == ["recipient@example.com"]
        # Optional fields should not be present
        assert "cc" not in result
        assert "body_text" not in result

    def test_to_dict_complete(self):
        """Test complete message detail serialization."""
        received_at = datetime(2024, 1, 1, 12, 0, 0)
        sent_at = datetime(2024, 1, 1, 11, 30, 0)

        message = MessageDetail(
            id="msg123",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            cc=["cc@example.com"],
            received_at=received_at,
            sent_at=sent_at,
            body_text="Hello world",
            headers={"Message-ID": "123@example.com"},
        )

        result = message.to_dict()
        assert result["received_at"] == "2024-01-01T12:00:00"
        assert result["sent_at"] == "2024-01-01T11:30:00"
        assert result["cc"] == ["cc@example.com"]
        assert result["body_text"] == "Hello world"
        assert result["headers"] == {"Message-ID": "123@example.com"}
