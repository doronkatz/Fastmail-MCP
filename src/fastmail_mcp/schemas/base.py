"""Base schema definitions for pagination and error handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class PaginationRequest:
    """Standard pagination parameters for MCP tools."""

    limit: int = 10
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("limit must be positive")
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        if self.limit > 100:
            raise ValueError("limit cannot exceed 100")


@dataclass
class PaginationResponse:
    """Standard pagination metadata in MCP tool responses."""

    limit: int
    offset: int
    total: Optional[int] = None
    has_more: Optional[bool] = None


@dataclass
class ErrorResponse:
    """Structured error response with troubleshooting guidance."""

    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    troubleshooting: Optional[str] = None

    @classmethod
    def auth_error(cls, message: str) -> "ErrorResponse":
        """Create authentication error with troubleshooting guidance."""
        return cls(
            error_type="AuthenticationError",
            message=message,
            troubleshooting=(
                "Check FASTMAIL_USERNAME and FASTMAIL_APP_PASSWORD in .env. "
                "Ensure app password is valid and not expired."
            ),
        )

    @classmethod
    def capability_error(cls, capability: str) -> "ErrorResponse":
        """Create capability error for missing JMAP features."""
        return cls(
            error_type="CapabilityError",
            message=f"JMAP capability '{capability}' not available",
            troubleshooting=(
                "This account may not have access to the requested feature. "
                "Contact your Fastmail administrator or check account permissions."
            ),
        )

    @classmethod
    def network_error(cls, message: str) -> "ErrorResponse":
        """Create network error with troubleshooting guidance."""
        return cls(
            error_type="NetworkError",
            message=message,
            troubleshooting=(
                "Check internet connectivity and Fastmail service status. "
                "Verify FASTMAIL_BASE_URL is correct."
            ),
        )

    @classmethod
    def validation_error(cls, field: str, message: str) -> "ErrorResponse":
        """Create input validation error."""
        return cls(
            error_type="ValidationError",
            message=f"Invalid {field}: {message}",
            details={"field": field},
        )
