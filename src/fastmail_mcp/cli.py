"""Command-line utilities for the Fastmail MCP agent."""

from __future__ import annotations

import argparse
import logging
import os
from typing import Sequence

from fastmail_mcp.client.transport import FastmailTransportError, JMAPTransport
from fastmail_mcp.utils import load_env

logger = logging.getLogger(__name__)


def _build_transport() -> JMAPTransport:
    base_url = os.environ.get("FASTMAIL_BASE_URL", "https://api.fastmail.com")
    username = os.environ.get("FASTMAIL_USERNAME", "local-user")
    app_password = os.environ.get("FASTMAIL_APP_PASSWORD", "local-app-password")
    token = os.environ.get("FASTMAIL_TOKEN")
    return JMAPTransport(
        base_url=base_url,
        username=username,
        app_password=app_password,
        token=token or None,
    )


def _uses_placeholder_credentials(username: str, app_password: str) -> bool:
    placeholders = {
        "local-user",
        "your.name@fastmail.com",
        "local-app-password",
        "app-specific-password",
    }
    if "obfuscated" in username:
        return True
    return username in placeholders or app_password in placeholders


def _is_capability_missing(error: FastmailTransportError) -> bool:
    message = str(error).lower()
    return "capability" in message and "unavailable for this account" in message


def _verify_optional(label: str, func) -> bool:
    try:
        items = func(limit=1)
    except FastmailTransportError as exc:
        if _is_capability_missing(exc):
            logger.info("%s capability unavailable; skipping.", label)
            return True
        logger.warning("%s verification failed: %s", label, exc)
        return False
    logger.info("%s OK: fetched %d item(s)", label, len(items))
    return True


def verify(_: argparse.Namespace) -> int:
    """Attempt a live query to confirm credentials work."""

    load_env()
    username = os.environ.get("FASTMAIL_USERNAME", "local-user")
    app_password = os.environ.get("FASTMAIL_APP_PASSWORD", "local-app-password")
    token = os.environ.get("FASTMAIL_TOKEN")
    if not token and _uses_placeholder_credentials(username, app_password):
        logger.warning(
            "Credentials appear to be placeholders; update .env before verifying."
        )
        return 1

    auth_label = "bearer token" if token else "app password"
    logger.info("Verifying Fastmail JMAP using %s auth", auth_label)

    transport = _build_transport()
    try:
        messages = transport.list_messages(limit=1)
    except FastmailTransportError as exc:
        logger.error("Mail verification failed: %s", exc)
        return 1
    logger.info("Mail OK: fetched %d message(s) for %s", len(messages), username)

    had_error = False
    if not _verify_optional("Contacts", transport.list_contacts):
        had_error = True
    if not _verify_optional("Events", transport.list_events):
        had_error = True

    return 1 if had_error else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fastmail MCP helper utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser(
        "verify", help="Validate live Fastmail connectivity"
    )
    verify_parser.set_defaults(func=verify)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
