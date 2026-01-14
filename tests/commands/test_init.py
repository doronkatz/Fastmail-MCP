"""Tests for commands initialization and registration."""

from unittest.mock import Mock

from fastmail_mcp.client import FastmailClient
from fastmail_mcp.commands import register_all


def test_register_all_calls_all_modules():
    """Test that register_all calls register on all command modules."""
    mock_server = Mock()
    mock_client = Mock(spec=FastmailClient)

    # Call register_all
    register_all(mock_server, mock_client)

    # Should register commands from all modules
    # messages: 4-5 commands depending on write tools
    # contacts: 1 command
    # events: 1 command
    # Total: 6-7 commands
    assert mock_server.register_command.call_count >= 6
    assert mock_server.register_command.call_count <= 7

    # Check that different command types were registered
    call_args = [call[0][0] for call in mock_server.register_command.call_args_list]
    assert "messages-list" in call_args
    assert "contacts-list" in call_args
    assert "events-list" in call_args
