"""Tests for the MCP server implementation."""

import os
from unittest.mock import AsyncMock, Mock, patch
import pytest

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, ServerCapabilities, ToolsCapability

from fastmail_mcp.mcp_server import build_client, create_server, main
from fastmail_mcp.client import FastmailClient


class TestBuildClient:
    """Test the build_client function."""

    @patch.dict(
        os.environ,
        {
            "FASTMAIL_BASE_URL": "https://test.fastmail.com",
            "FASTMAIL_USERNAME": "test@example.com",
            "FASTMAIL_APP_PASSWORD": "test-password",
            "FASTMAIL_TOKEN": "test-token",
        },
        clear=True,
    )
    def test_build_client_with_all_env_vars(self):
        """Test building client with all environment variables set."""
        client = build_client()

        assert isinstance(client, FastmailClient)
        assert client.base_url == "https://test.fastmail.com"
        assert client.username == "test@example.com"
        assert client.app_password == "test-password"
        assert client.token == "test-token"

    @patch.dict(
        os.environ,
        {
            "FASTMAIL_USERNAME": "test@example.com",
            "FASTMAIL_APP_PASSWORD": "test-password",
        },
        clear=True,
    )
    @patch("fastmail_mcp.mcp_server.load_env")
    def test_build_client_with_defaults(self, mock_load_env):
        """Test building client with default values."""
        client = build_client()

        assert isinstance(client, FastmailClient)
        assert client.base_url == "https://api.fastmail.com"
        assert client.username == "test@example.com"
        assert client.app_password == "test-password"
        assert client.token is None

    @patch.dict(os.environ, {}, clear=True)
    @patch("fastmail_mcp.mcp_server.load_env")
    def test_build_client_with_fallback_values(self, mock_load_env):
        """Test building client with fallback values when no env vars set."""
        client = build_client()

        assert isinstance(client, FastmailClient)
        assert client.base_url == "https://api.fastmail.com"
        assert client.username == "local-user"
        assert client.app_password == "local-app-password"
        assert client.token is None

    @patch.dict(
        os.environ,
        {"FASTMAIL_TOKEN": ""},  # Empty string should be converted to None
        clear=True,
    )
    @patch("fastmail_mcp.mcp_server.load_env")
    def test_build_client_empty_token_becomes_none(self, mock_load_env):
        """Test that empty token string becomes None."""
        client = build_client()
        assert client.token is None

    @patch("fastmail_mcp.mcp_server.load_env")
    @patch("fastmail_mcp.mcp_server.Path")
    def test_build_client_loads_env_file(self, mock_path, mock_load_env):
        """Test that build_client attempts to load .env file from project root."""
        # Mock the path resolution
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_path.return_value.parent.parent.parent.__truediv__.return_value = mock_file

        build_client()

        # Verify load_env was called with the .env file
        mock_load_env.assert_called_once_with(mock_file)

    @patch("fastmail_mcp.mcp_server.load_env")
    @patch("fastmail_mcp.mcp_server.Path")
    def test_build_client_handles_missing_env_file(self, mock_path, mock_load_env):
        """Test that build_client handles missing .env file gracefully."""
        # Mock the path resolution with non-existent file
        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_path.return_value.parent.parent.parent.__truediv__.return_value = mock_file

        build_client()

        # Verify load_env was called with None when file doesn't exist
        mock_load_env.assert_called_once_with(None)


class TestCreateServer:
    """Test the create_server function."""

    @patch("fastmail_mcp.mcp_server.build_client")
    def test_create_server_returns_server_instance(self, mock_build_client):
        """Test that create_server returns a Server instance."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client

        server = create_server()

        assert isinstance(server, Server)
        assert server.name == "fastmail-mcp"
        mock_build_client.assert_called_once()

    @patch('fastmail_mcp.mcp_server.build_client')
    def test_list_tools_returns_expected_tools(self, mock_build_client):
        """Test that list_tools returns all expected MCP tools."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client
        
        server = create_server()
        
        # Mock the async behavior by directly calling the decorated function
        # The @server.list_tools() decorator creates a handler we can access
        handler = None
        for handler_info in server._list_tools_handlers:
            handler = handler_info.func
            break
        
        # Create a mock coroutine result
        import asyncio
        tools = asyncio.run(handler())
        
        assert len(tools) == 5
        tool_names = [tool.name for tool in tools]
        expected_names = [
            "messages-list",
            "messages-search", 
            "messages-get",
            "contacts-list",
            "events-list"
        ]
        assert tool_names == expected_names

    @patch("fastmail_mcp.mcp_server.build_client")
    @pytest.mark.asyncio
    async def test_list_tools_tool_schemas_are_valid(self, mock_build_client):
        """Test that all tool schemas have proper structure."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client

        server = create_server()
        tools = await server._list_tools_handler()

        for tool in tools:
            assert isinstance(tool, Tool)
            assert tool.name
            assert tool.description
            assert "inputSchema" in tool.model_dump()

            # Verify schema structure
            schema = tool.inputSchema
            assert schema["type"] == "object"
            assert "properties" in schema


class TestCallTool:
    """Test the call_tool functionality."""

    @patch("fastmail_mcp.mcp_server.build_client")
    @patch("fastmail_mcp.mcp_server.list_messages")
    @pytest.mark.asyncio
    async def test_call_tool_messages_list(self, mock_list_messages, mock_build_client):
        """Test calling messages-list tool."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client
        mock_list_messages.return_value = {"messages": ["test message"]}

        server = create_server()

        # Call the tool
        result = await server._call_tool_handler("messages-list", {"limit": "10"})

        # Verify the call
        mock_list_messages.assert_called_once_with(client=mock_client, limit=10)
        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "test message" in result[0]["text"]

    @patch("fastmail_mcp.mcp_server.build_client")
    @patch("fastmail_mcp.mcp_server.search_messages")
    @pytest.mark.asyncio
    async def test_call_tool_messages_search(
        self, mock_search_messages, mock_build_client
    ):
        """Test calling messages-search tool."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client
        mock_search_messages.return_value = {"messages": ["search result"]}

        server = create_server()

        # Call the tool with various arguments
        result = await server._call_tool_handler(
            "messages-search",
            {"limit": "5", "offset": "10", "sender": "test@example.com"},
        )

        # Verify the call with proper type conversions
        mock_search_messages.assert_called_once_with(
            client=mock_client, limit=5, offset=10, sender="test@example.com"
        )
        assert len(result) == 1
        assert result[0]["type"] == "text"

    @patch("fastmail_mcp.mcp_server.build_client")
    @patch("fastmail_mcp.mcp_server.get_message")
    @pytest.mark.asyncio
    async def test_call_tool_messages_get(self, mock_get_message, mock_build_client):
        """Test calling messages-get tool."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client
        mock_get_message.return_value = {"message": "full message details"}

        server = create_server()

        # Call the tool
        result = await server._call_tool_handler(
            "messages-get", {"message_id": "msg123"}
        )

        # Verify the call
        mock_get_message.assert_called_once_with(
            client=mock_client, message_id="msg123"
        )
        assert len(result) == 1
        assert result[0]["type"] == "text"

    @patch("fastmail_mcp.mcp_server.build_client")
    @patch("fastmail_mcp.mcp_server.list_contacts")
    @pytest.mark.asyncio
    async def test_call_tool_contacts_list(self, mock_list_contacts, mock_build_client):
        """Test calling contacts-list tool."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client
        mock_list_contacts.return_value = {"contacts": ["contact1", "contact2"]}

        server = create_server()

        # Call the tool
        result = await server._call_tool_handler("contacts-list", {"limit": "20"})

        # Verify the call
        mock_list_contacts.assert_called_once_with(client=mock_client, limit=20)
        assert len(result) == 1
        assert result[0]["type"] == "text"

    @patch("fastmail_mcp.mcp_server.build_client")
    @patch("fastmail_mcp.mcp_server.list_events")
    @pytest.mark.asyncio
    async def test_call_tool_events_list(self, mock_list_events, mock_build_client):
        """Test calling events-list tool."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client
        mock_list_events.return_value = {"events": ["event1", "event2"]}

        server = create_server()

        # Call the tool
        result = await server._call_tool_handler("events-list", {"limit": "15"})

        # Verify the call
        mock_list_events.assert_called_once_with(client=mock_client, limit=15)
        assert len(result) == 1
        assert result[0]["type"] == "text"

    @patch("fastmail_mcp.mcp_server.build_client")
    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool_raises_error(self, mock_build_client):
        """Test that calling unknown tool raises ValueError."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client

        server = create_server()

        # Attempt to call unknown tool
        with pytest.raises(ValueError, match="Unknown tool: unknown-tool"):
            await server._call_tool_handler("unknown-tool", {})

    @patch("fastmail_mcp.mcp_server.build_client")
    @pytest.mark.asyncio
    async def test_call_tool_handles_missing_limit_gracefully(self, mock_build_client):
        """Test that tools handle missing limit parameter gracefully."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client

        server = create_server()

        with patch("fastmail_mcp.mcp_server.list_messages") as mock_list_messages:
            mock_list_messages.return_value = {"messages": []}

            # Call without limit parameter
            await server._call_tool_handler("messages-list", {})

            # Verify limit was not passed
            mock_list_messages.assert_called_once_with(client=mock_client)


class TestMain:
    """Test the main entry point."""

    @patch("fastmail_mcp.mcp_server.create_server")
    @patch("fastmail_mcp.mcp_server.stdio_server")
    @pytest.mark.asyncio
    async def test_main_creates_server_and_runs(
        self, mock_stdio_server, mock_create_server
    ):
        """Test that main creates server and runs with stdio transport."""
        # Mock server and stdio streams
        mock_server = AsyncMock()
        mock_create_server.return_value = mock_server

        mock_streams = (AsyncMock(), AsyncMock())
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_streams
        mock_stdio_server.return_value = mock_context_manager

        # Run main
        await main()

        # Verify server was created and run was called
        mock_create_server.assert_called_once()
        mock_server.run.assert_called_once()

        # Verify the initialization options
        call_args = mock_server.run.call_args
        assert len(call_args[0]) == 3  # streams[0], streams[1], InitializationOptions

        init_options = call_args[0][2]
        assert isinstance(init_options, InitializationOptions)
        assert init_options.server_name == "fastmail-mcp"
        assert init_options.server_version == "0.1.0"
        assert isinstance(init_options.capabilities, ServerCapabilities)
        assert isinstance(init_options.capabilities.tools, ToolsCapability)
        assert init_options.capabilities.tools.listChanged is False

    @patch("fastmail_mcp.mcp_server.main")
    @patch("asyncio.run")
    def test_main_module_execution(self, mock_asyncio_run, mock_main):
        """Test that running module calls main through asyncio.run."""
        # This would test the if __name__ == "__main__" block
        # We can't directly test it, but we can verify the imports work
        from fastmail_mcp import mcp_server

        # Verify main function exists and is callable
        assert callable(mcp_server.main)
        assert callable(mcp_server.create_server)
        assert callable(mcp_server.build_client)


class TestIntegration:
    """Integration tests for the MCP server."""

    @patch("fastmail_mcp.mcp_server.build_client")
    @pytest.mark.asyncio
    async def test_server_tools_and_calls_integration(self, mock_build_client):
        """Test that tools can be listed and called in sequence."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client

        server = create_server()

        # First list the tools
        tools = await server._list_tools_handler()
        assert len(tools) == 5

        # Then try calling each tool
        with patch(
            "fastmail_mcp.mcp_server.list_messages", return_value={"messages": []}
        ):
            result = await server._call_tool_handler("messages-list", {})
            assert len(result) == 1
            assert result[0]["type"] == "text"

        with patch(
            "fastmail_mcp.mcp_server.list_contacts", return_value={"contacts": []}
        ):
            result = await server._call_tool_handler("contacts-list", {})
            assert len(result) == 1
            assert result[0]["type"] == "text"
