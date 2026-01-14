"""Tests for enhanced transport functionality."""

from fastmail_mcp.client.transport import FastmailTransportError


class TestFastmailTransportError:

    def test_auth_error_creation(self):
        """Test authentication error creation."""
        error = FastmailTransportError.auth_error("Invalid credentials")

        assert error.error_type == "AuthenticationError"
        assert error.message == "Invalid credentials"
        assert "FASTMAIL_USERNAME" in error.troubleshooting
        assert "FASTMAIL_APP_PASSWORD" in error.troubleshooting

    def test_capability_error_creation(self):
        """Test capability error creation."""
        capability = "urn:ietf:params:jmap:mail"
        error = FastmailTransportError.capability_error(capability)

        assert error.error_type == "CapabilityError"
        assert capability in error.message
        assert "account permissions" in error.troubleshooting

    def test_network_error_creation(self):
        """Test network error creation."""
        error = FastmailTransportError.network_error("Connection timeout")

        assert error.error_type == "NetworkError"
        assert error.message == "Connection timeout"
        assert "connectivity" in error.troubleshooting
        assert "FASTMAIL_BASE_URL" in error.troubleshooting

    def test_error_inheritance(self):
        """Test that enhanced errors are still RuntimeError instances."""
        error = FastmailTransportError.auth_error("Test")

        assert isinstance(error, RuntimeError)
        assert isinstance(error, FastmailTransportError)

    def test_default_error_type(self):
        """Test default error type when not specified."""
        error = FastmailTransportError("Generic error")

        assert error.error_type == "TransportError"
        assert error.message == "Generic error"
        assert error.troubleshooting is None
