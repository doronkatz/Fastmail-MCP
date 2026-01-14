"""Tests for enhanced message commands with search and filtering capabilities."""

from unittest.mock import Mock, patch
from datetime import datetime

from fastmail_mcp.client import FastmailClient
from fastmail_mcp.commands.messages import (
    search_messages,
    get_message,
    list_mailboxes,
    send_message,
    _is_write_enabled,
    _dict_to_message_summary,
    _dict_to_message_detail,
    _dict_to_mailbox_info,
    COMMAND_MESSAGES_SEARCH,
    COMMAND_MESSAGES_GET,
    COMMAND_MAILBOXES_LIST,
    COMMAND_MESSAGES_SEND,
)


class TestEnhancedMessageCommands:

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=FastmailClient)

    def test_search_messages_basic(self):
        """Test basic message search functionality."""
        # Mock transport response
        self.mock_client.search_messages.return_value = {
            "messages": [
                {
                    "id": "msg1",
                    "subject": "Test",
                    "sender": "test@example.com",
                    "snippet": "Hello world",
                    "received_at": "2024-01-01T12:00:00Z",
                    "read": True,
                    "has_attachment": False,
                    "mailbox": "inbox",
                }
            ],
            "total": 1,
            "position": 0,
            "limit": 10,
        }

        result = search_messages(
            client=self.mock_client, sender="test@example.com", limit=10
        )

        assert "messages" in result
        assert "pagination" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0]["sender"] == "test@example.com"
        assert result["pagination"]["total"] == 1

    def test_search_messages_with_date_filter(self):
        """Test message search with date range filtering."""
        self.mock_client.search_messages.return_value = {
            "messages": [],
            "total": 0,
            "position": 0,
            "limit": 10,
        }

        result = search_messages(
            client=self.mock_client,
            date_start="2024-01-01T00:00:00Z",
            date_end="2024-01-31T23:59:59Z",
            has_attachment=True,
        )

        # Verify the client was called with correct parameters
        self.mock_client.search_messages.assert_called_once()
        assert result["pagination"]["total"] == 0

    def test_search_messages_invalid_date(self):
        """Test search with invalid date format."""
        result = search_messages(client=self.mock_client, date_start="invalid-date")

        assert "error" in result
        assert result["error"]["error_type"] == "ValidationError"

    def test_search_messages_transport_error(self):
        """Test search handling transport errors."""
        from fastmail_mcp.client.transport import FastmailTransportError

        self.mock_client.search_messages.side_effect = FastmailTransportError(
            "Network error"
        )

        result = search_messages(client=self.mock_client)

        assert "error" in result
        assert result["error"]["error_type"] == "NetworkError"

    def test_get_message_basic(self):
        """Test basic message retrieval."""
        self.mock_client.get_message.return_value = {
            "id": "msg123",
            "subject": "Test Message",
            "sender": "test@example.com",
            "to": ["recipient@example.com"],
            "received_at": "2024-01-01T12:00:00Z",
            "body_text": "Hello world",
        }

        result = get_message(
            client=self.mock_client, message_id="msg123", include_body=True
        )

        assert "message" in result
        assert result["message"]["id"] == "msg123"
        assert result["message"]["subject"] == "Test Message"
        assert result["message"]["body_text"] == "Hello world"

    def test_get_message_empty_id(self):
        """Test get message with empty ID."""
        result = get_message(client=self.mock_client, message_id="")

        assert "error" in result
        assert result["error"]["error_type"] == "ValidationError"

    def test_get_message_transport_error(self):
        """Test get message handling transport errors."""
        from fastmail_mcp.client.transport import FastmailTransportError

        self.mock_client.get_message.side_effect = FastmailTransportError(
            "Message not found"
        )

        result = get_message(client=self.mock_client, message_id="msg123")

        assert "error" in result
        assert result["error"]["error_type"] == "NetworkError"

    def test_list_mailboxes_basic(self):
        """Test basic mailbox listing."""
        self.mock_client.list_mailboxes.return_value = {
            "mailboxes": [
                {
                    "id": "inbox",
                    "name": "Inbox",
                    "parent_id": None,
                    "unread_count": 5,
                    "total_count": 100,
                }
            ],
            "total": 1,
            "position": 0,
            "limit": 50,
        }

        result = list_mailboxes(client=self.mock_client)

        assert "mailboxes" in result
        assert "pagination" in result
        assert len(result["mailboxes"]) == 1
        assert result["mailboxes"][0]["name"] == "Inbox"
        assert result["mailboxes"][0]["unread_count"] == 5

    def test_list_mailboxes_transport_error(self):
        """Test mailbox listing with transport error."""
        from fastmail_mcp.client.transport import FastmailTransportError

        self.mock_client.list_mailboxes.side_effect = FastmailTransportError(
            "Connection failed"
        )

        result = list_mailboxes(client=self.mock_client)

        assert "error" in result
        assert result["error"]["error_type"] == "NetworkError"

    @patch.dict("os.environ", {"FASTMAIL_ENABLE_WRITE_TOOLS": "false"})
    def test_send_message_write_disabled(self):
        """Test send message when write operations are disabled."""
        result = send_message(
            client=self.mock_client,
            to=["test@example.com"],
            subject="Test",
            body_text="Hello world",
        )

        assert "error" in result
        assert result["error"]["error_type"] == "PermissionDenied"

    @patch.dict("os.environ", {"FASTMAIL_ENABLE_WRITE_TOOLS": "true"})
    def test_send_message_write_enabled(self):
        """Test send message when write operations are enabled."""
        result = send_message(
            client=self.mock_client,
            to=["test@example.com"],
            subject="Test",
            body_text="Hello world",
        )

        assert "message_id" in result
        assert "note" in result  # Placeholder implementation note
        assert result["success"] is False  # Not yet implemented

    @patch.dict("os.environ", {"FASTMAIL_ENABLE_WRITE_TOOLS": "true"})
    def test_send_message_validation_errors(self):
        """Test send message validation errors when write is enabled."""
        # Empty to field
        result = send_message(
            client=self.mock_client, to=[], subject="Test", body_text="Hello"
        )
        assert "error" in result
        assert result["error"]["error_type"] == "ValidationError"

        # Empty subject
        result = send_message(
            client=self.mock_client,
            to=["test@example.com"],
            subject="",
            body_text="Hello",
        )
        assert "error" in result
        assert result["error"]["error_type"] == "ValidationError"

        # No body content
        result = send_message(
            client=self.mock_client, to=["test@example.com"], subject="Test"
        )
        assert "error" in result
        assert result["error"]["error_type"] == "ValidationError"

    @patch.dict("os.environ", {}, clear=True)
    def test_is_write_enabled_default(self):
        """Test write enabled check with default environment."""
        assert _is_write_enabled() is False

    @patch.dict("os.environ", {"FASTMAIL_ENABLE_WRITE_TOOLS": "TRUE"})
    def test_is_write_enabled_case_insensitive(self):
        """Test write enabled check is case insensitive."""
        assert _is_write_enabled() is True

    def test_dict_to_message_summary(self):
        """Test conversion from dict to MessageSummary."""
        data = {
            "id": "msg1",
            "subject": "Test",
            "sender": "test@example.com",
            "snippet": "Hello",
            "received_at": "2024-01-01T12:00:00Z",
            "read": True,
            "has_attachment": False,
            "mailbox": "inbox",
        }

        message = _dict_to_message_summary(data)

        assert message.id == "msg1"
        assert message.subject == "Test"
        assert message.sender == "test@example.com"
        assert message.read is True
        assert isinstance(message.received_at, datetime)

    def test_dict_to_message_detail(self):
        """Test conversion from dict to MessageDetail."""
        data = {
            "id": "msg1",
            "subject": "Test",
            "sender": "test@example.com",
            "to": ["recipient@example.com"],
            "received_at": "2024-01-01T12:00:00Z",
            "sent_at": "2024-01-01T11:30:00Z",
            "body_text": "Hello world",
        }

        message = _dict_to_message_detail(data)

        assert message.id == "msg1"
        assert message.subject == "Test"
        assert message.to == ["recipient@example.com"]
        assert message.body_text == "Hello world"
        assert isinstance(message.received_at, datetime)
        assert isinstance(message.sent_at, datetime)

    def test_dict_to_mailbox_info(self):
        """Test conversion from dict to MailboxInfo."""
        data = {
            "id": "inbox",
            "name": "Inbox",
            "parent_id": None,
            "unread_count": 5,
            "total_count": 100,
        }

        mailbox = _dict_to_mailbox_info(data)

        assert mailbox.id == "inbox"
        assert mailbox.name == "Inbox"
        assert mailbox.parent_id is None
        assert mailbox.unread_count == 5
        assert mailbox.total_count == 100

    def test_command_constants(self):
        """Test that command constants are properly defined."""
        assert COMMAND_MESSAGES_SEARCH == "messages-search"
        assert COMMAND_MESSAGES_GET == "messages-get"
        assert COMMAND_MAILBOXES_LIST == "mailboxes-list"
        assert COMMAND_MESSAGES_SEND == "messages-send"

    @patch.dict("os.environ", {"FASTMAIL_ENABLE_WRITE_TOOLS": "true"})
    def test_command_registration_with_write_enabled(self):
        """Test command registration when write tools are enabled."""
        from fastmail_mcp.commands.messages import register

        mock_server = Mock()

        # Mock the server register_command method
        mock_server.register_command = Mock()

        register(mock_server, self.mock_client)

        # Should register 5 commands (4 read + 1 write)
        assert mock_server.register_command.call_count == 5

        # Check that messages-send was registered
        call_args = [call[0][0] for call in mock_server.register_command.call_args_list]
        assert COMMAND_MESSAGES_SEND in call_args

    @patch.dict("os.environ", {}, clear=True)
    def test_command_registration_with_write_disabled(self):
        """Test command registration when write tools are disabled."""
        from fastmail_mcp.commands.messages import register

        mock_server = Mock()
        mock_server.register_command = Mock()

        register(mock_server, self.mock_client)

        # Should register 4 commands (read only)
        assert mock_server.register_command.call_count == 4

        # Check that messages-send was NOT registered
        call_args = [call[0][0] for call in mock_server.register_command.call_args_list]
        assert COMMAND_MESSAGES_SEND not in call_args

    def test_search_with_complex_filter_conversion(self):
        """Test search with complex filter that exercises conversion logic."""
        self.mock_client.search_messages.return_value = {
            "messages": [],
            "total": 0,
            "position": 0,
            "limit": 10,
        }

        # Test with mailbox filter to exercise JMAP conversion
        result = search_messages(
            client=self.mock_client,
            mailbox="INBOX",
            sender="specific@example.com",
            subject="Important Meeting",
            read=True,
            has_attachment=True,
        )

        assert "messages" in result
        # Verify client was called (exercises the filter conversion path)
        self.mock_client.search_messages.assert_called_once()
