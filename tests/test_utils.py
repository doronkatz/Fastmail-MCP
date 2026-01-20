"""Tests for the utils module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from fastmail_mcp.utils import load_env, get_required_env


class TestLoadEnv:
    """Test the load_env function."""

    def test_load_env_with_valid_file(self):
        """Test loading env vars from a valid .env file."""
        env_content = """
# This is a comment
KEY1=value1
KEY2=value2
// Another comment style
KEY3=value with spaces
EMPTY_KEY=
KEY4=value4
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()
            env_path = Path(f.name)

        try:
            # Clear any existing env vars that might interfere
            for key in ["KEY1", "KEY2", "KEY3", "KEY4", "EMPTY_KEY"]:
                os.environ.pop(key, None)

            result = load_env(env_path)

            # Verify environment variables were set
            assert os.environ.get("KEY1") == "value1"
            assert os.environ.get("KEY2") == "value2"
            assert os.environ.get("KEY3") == "value with spaces"
            assert os.environ.get("KEY4") == "value4"
            assert os.environ.get("EMPTY_KEY") == ""

            # Verify return value includes all env vars (not just the ones we set)
            assert "KEY1" in result
            assert "KEY2" in result
            assert result["KEY1"] == "value1"
            assert result["KEY2"] == "value2"

        finally:
            # Clean up
            env_path.unlink()
            for key in ["KEY1", "KEY2", "KEY3", "KEY4", "EMPTY_KEY"]:
                os.environ.pop(key, None)

    def test_load_env_does_not_override_existing(self):
        """Test that load_env does not override existing environment variables."""
        env_content = """
EXISTING_KEY=new_value
NEW_KEY=new_value
"""
        # Set an existing environment variable
        os.environ["EXISTING_KEY"] = "original_value"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()
            env_path = Path(f.name)

        try:
            load_env(env_path)

            # Verify existing key was not overridden
            assert os.environ["EXISTING_KEY"] == "original_value"
            # Verify new key was set
            assert os.environ.get("NEW_KEY") == "new_value"

        finally:
            # Clean up
            env_path.unlink()
            os.environ.pop("EXISTING_KEY", None)
            os.environ.pop("NEW_KEY", None)

    def test_load_env_with_nonexistent_file(self):
        """Test load_env with a non-existent file."""
        nonexistent_path = Path("/nonexistent/path/.env")

        # Should not raise an error, just return current env
        result = load_env(nonexistent_path)

        # Should return current environment variables
        assert isinstance(result, dict)
        # Should contain at least PATH (assuming it exists)
        if "PATH" in os.environ:
            assert "PATH" in result

    def test_load_env_with_malformed_lines(self):
        """Test load_env handles malformed lines gracefully."""
        env_content = """
VALID_KEY=valid_value
invalid_line_no_equals
ANOTHER_VALID=another_value
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()
            env_path = Path(f.name)

        try:
            # Clear any existing env vars
            for key in ["VALID_KEY", "ANOTHER_VALID"]:
                os.environ.pop(key, None)

            load_env(env_path)

            # Only valid lines should be processed
            assert os.environ.get("VALID_KEY") == "valid_value"
            assert os.environ.get("ANOTHER_VALID") == "another_value"
            # Invalid lines should be ignored (no error raised)

        finally:
            env_path.unlink()
            for key in ["VALID_KEY", "ANOTHER_VALID"]:
                os.environ.pop(key, None)

    def test_load_env_with_empty_file(self):
        """Test load_env with an empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("")
            f.flush()
            env_path = Path(f.name)

        try:
            result = load_env(env_path)
            # Should return current environment without errors
            assert isinstance(result, dict)

        finally:
            env_path.unlink()

    def test_load_env_with_only_comments(self):
        """Test load_env with file containing only comments."""
        env_content = """
# Comment 1
// Comment 2
# Another comment
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()
            env_path = Path(f.name)

        try:
            result = load_env(env_path)
            # Should return current environment without setting any new vars
            assert isinstance(result, dict)

        finally:
            env_path.unlink()

    def test_load_env_default_path(self):
        """Test load_env with default path (.env)."""
        # Mock Path.exists() to return False for default path
        with patch("fastmail_mcp.utils.Path") as mock_path:
            mock_env_path = mock_path.return_value
            mock_env_path.exists.return_value = False

            result = load_env()

            # Should have tried to use Path(".env")
            mock_path.assert_called_once_with(".env")
            mock_env_path.exists.assert_called_once()
            assert isinstance(result, dict)

    def test_load_env_with_equals_in_value(self):
        """Test load_env handles values that contain equals signs."""
        env_content = """
URL=https://api.example.com/path?param=value&other=test
BASE64=dGVzdD0=test
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()
            env_path = Path(f.name)

        try:
            # Clear any existing env vars
            for key in ["URL", "BASE64"]:
                os.environ.pop(key, None)

            load_env(env_path)

            # Values with equals should be handled correctly
            assert (
                os.environ.get("URL")
                == "https://api.example.com/path?param=value&other=test"
            )
            assert os.environ.get("BASE64") == "dGVzdD0=test"

        finally:
            env_path.unlink()
            for key in ["URL", "BASE64"]:
                os.environ.pop(key, None)

    def test_load_env_strips_whitespace(self):
        """Test that load_env strips whitespace from keys and values."""
        env_content = """
  SPACED_KEY  =  spaced value  
NORMAL_KEY=normal_value
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()
            env_path = Path(f.name)

        try:
            # Clear any existing env vars
            for key in ["SPACED_KEY", "NORMAL_KEY"]:
                os.environ.pop(key, None)

            load_env(env_path)

            # Whitespace should be stripped
            assert os.environ.get("SPACED_KEY") == "spaced value"
            assert os.environ.get("NORMAL_KEY") == "normal_value"

        finally:
            env_path.unlink()
            for key in ["SPACED_KEY", "NORMAL_KEY"]:
                os.environ.pop(key, None)


class TestGetRequiredEnv:
    """Test the get_required_env function."""

    def test_get_required_env_success(self):
        """Test get_required_env with existing non-empty variable."""
        test_key = "TEST_REQUIRED_VAR"
        test_value = "test_value"

        os.environ[test_key] = test_value
        try:
            result = get_required_env(test_key)
            assert result == test_value
        finally:
            os.environ.pop(test_key, None)

    def test_get_required_env_missing_key(self):
        """Test get_required_env with missing environment variable."""
        missing_key = "DEFINITELY_MISSING_KEY"

        # Ensure the key doesn't exist
        os.environ.pop(missing_key, None)

        with pytest.raises(
            RuntimeError, match=f"Missing required environment variable: {missing_key}"
        ):
            get_required_env(missing_key)

    def test_get_required_env_empty_value(self):
        """Test get_required_env with empty environment variable."""
        empty_key = "EMPTY_TEST_VAR"

        os.environ[empty_key] = ""
        try:
            with pytest.raises(
                RuntimeError, match=f"Environment variable {empty_key} is empty"
            ):
                get_required_env(empty_key)
        finally:
            os.environ.pop(empty_key, None)

    def test_get_required_env_whitespace_only_value(self):
        """Test get_required_env with whitespace-only value."""
        whitespace_key = "WHITESPACE_TEST_VAR"

        os.environ[whitespace_key] = "   "
        try:
            # This should succeed since we check for truthiness, not just emptiness
            result = get_required_env(whitespace_key)
            assert result == "   "
        finally:
            os.environ.pop(whitespace_key, None)

    def test_get_required_env_zero_string_value(self):
        """Test get_required_env with '0' as value (should be valid)."""
        zero_key = "ZERO_TEST_VAR"

        os.environ[zero_key] = "0"
        try:
            result = get_required_env(zero_key)
            assert result == "0"
        finally:
            os.environ.pop(zero_key, None)

    def test_get_required_env_exception_chaining(self):
        """Test that get_required_env properly chains KeyError exception."""
        missing_key = "CHAIN_TEST_MISSING_KEY"

        # Ensure the key doesn't exist
        os.environ.pop(missing_key, None)

        try:
            get_required_env(missing_key)
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            # Verify the exception was properly chained
            assert isinstance(e.__cause__, KeyError)
            assert str(e.__cause__).strip("'") == missing_key


class TestUtilsIntegration:
    """Integration tests for utils module functions."""

    def test_load_env_and_get_required_env_integration(self):
        """Test load_env and get_required_env working together."""
        env_content = """
INTEGRATION_KEY=integration_value
REQUIRED_KEY=required_value
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()
            env_path = Path(f.name)

        try:
            # Clear any existing env vars
            for key in ["INTEGRATION_KEY", "REQUIRED_KEY"]:
                os.environ.pop(key, None)

            # Load env file
            result = load_env(env_path)

            # Then use get_required_env to retrieve values
            integration_val = get_required_env("INTEGRATION_KEY")
            required_val = get_required_env("REQUIRED_KEY")

            assert integration_val == "integration_value"
            assert required_val == "required_value"
            assert "INTEGRATION_KEY" in result
            assert "REQUIRED_KEY" in result

        finally:
            env_path.unlink()
            for key in ["INTEGRATION_KEY", "REQUIRED_KEY"]:
                os.environ.pop(key, None)
