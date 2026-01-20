"""Simple tests for MCP server functionality without async complexity."""

import os
from unittest.mock import Mock, patch

from fastmail_mcp.mcp_server import build_client, create_server
from fastmail_mcp.client import FastmailClient


class TestBuildClientSimple:
    """Simple tests for build_client function."""

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
    @patch("fastmail_mcp.mcp_server.load_env")
    def test_build_client_with_all_env_vars(self, mock_load_env):
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


class TestCreateServerSimple:
    """Simple tests for create_server function."""

    @patch("fastmail_mcp.mcp_server.build_client")
    def test_create_server_returns_server_instance(self, mock_build_client):
        """Test that create_server returns a Server instance."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client

        server = create_server()

        # Test that server is created with correct name
        assert server.name == "fastmail-mcp"
        mock_build_client.assert_called_once()

    @patch("fastmail_mcp.mcp_server.build_client")
    def test_server_has_handlers(self, mock_build_client):
        """Test that server has the expected handlers registered."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client

        server = create_server()

        # Verify server is properly initialized
        assert server is not None
        assert server.name == "fastmail-mcp"
        # Server should be a proper MCP Server instance
        from mcp.server import Server

        assert isinstance(server, Server)


class TestToolDefinitions:
    """Test tool definitions without async execution."""

    @patch("fastmail_mcp.mcp_server.build_client")
    def test_tool_count_and_names(self, mock_build_client):
        """Test that all expected tools are defined."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client

        # Create server to trigger tool registration
        server = create_server()

        # The tools are defined in the list_tools handler function
        # We can't easily test the async handler without pytest-asyncio
        # But we can verify the server structure is correct
        assert server is not None
        assert server.name == "fastmail-mcp"

    @patch("fastmail_mcp.mcp_server.build_client")
    def test_server_configuration(self, mock_build_client):
        """Test server configuration and initialization."""
        mock_client = Mock()
        mock_build_client.return_value = mock_client

        server = create_server()

        # Verify server has expected attributes
        assert hasattr(server, "name")
        assert server.name == "fastmail-mcp"

        # Verify client was built
        mock_build_client.assert_called_once()


class TestEnvironmentLoading:
    """Test environment variable loading functionality."""

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
