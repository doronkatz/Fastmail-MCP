"""Minimal Model Context Protocol server harness for Fastmail."""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import socketserver
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, IO, Mapping

from fastmail_mcp.client import FastmailClient
from fastmail_mcp.commands import register_all
from fastmail_mcp.utils import load_env

logger = logging.getLogger(__name__)


CommandHandler = Callable[..., Any]


@dataclass
class CommandDefinition:
    handler: CommandHandler
    description: str


class FastmailMCPServer:
    """Lightweight command dispatcher for the Model Context Protocol."""

    def __init__(self, client: FastmailClient) -> None:
        self._client = client
        self._commands: Dict[str, CommandDefinition] = {}

    def register_command(
        self, name: str, *, handler: CommandHandler, description: str = ""
    ) -> None:
        if name in self._commands:
            raise ValueError(f"Command '{name}' is already registered")
        self._commands[name] = CommandDefinition(handler=handler, description=description)

    def handle_call(self, name: str, params: Mapping[str, Any] | None = None) -> Any:
        if name not in self._commands:
            raise KeyError(f"Unknown command: {name}")
        command = self._commands[name]
        params = dict(params or {})
        return command.handler(**params)

    def handle_request(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        command_name = payload.get("command")
        if not command_name:
            return {
                "error": {
                    "type": "InvalidRequest",
                    "message": "Missing command name",
                }
            }
        params = payload.get("params") or {}
        try:
            result = self.handle_call(command_name, params)
            return {"command": command_name, "result": result}
        except Exception as exc:  # pragma: no cover - logged for observability
            logger.exception("Command %s failed", command_name)
            return {
                "command": command_name,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                },
            }

    def handle_stream(self, reader: IO[str], writer: IO[str]) -> None:
        for raw_line in reader:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Invalid JSON input: %s", exc)
                response = {
                    "error": {
                        "type": "InvalidJSON",
                        "message": str(exc),
                    }
                }
            else:
                response = self.handle_request(payload)
            writer.write(json.dumps(response) + "\n")
            writer.flush()

    def serve_forever(
        self,
        *,
        input_stream: IO[str] | None = None,
        output_stream: IO[str] | None = None,
    ) -> None:
        reader = input_stream or sys.stdin
        writer = output_stream or sys.stdout
        self.handle_stream(reader, writer)


class _MCPTCPRequestHandler(socketserver.StreamRequestHandler):
    """socketserver handler that proxies JSON lines to the dispatcher."""

    def handle(self) -> None:  # pragma: no cover - integration layer
        dispatcher: FastmailMCPServer = getattr(self.server, "dispatcher")  # type: ignore[attr-defined]
        reader = io.TextIOWrapper(self.rfile, encoding="utf-8")
        writer = io.TextIOWrapper(
            self.wfile,
            encoding="utf-8",
            write_through=True,
        )
        dispatcher.handle_stream(reader, writer)


class MCPTCPServer(socketserver.ThreadingTCPServer):
    """Thread-per-connection TCP server that reuses the command dispatcher."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], dispatcher: FastmailMCPServer):
        super().__init__(server_address, _MCPTCPRequestHandler)
        self.dispatcher = dispatcher


def serve_tcp(dispatcher: FastmailMCPServer, host: str, port: int) -> None:
    """Start a TCP listener that wraps the stdio dispatcher."""

    with MCPTCPServer((host, port), dispatcher) as tcp_server:  # pragma: no cover - network wrapper
        logger.info(
            "Fastmail MCP server listening on %s:%d (TCP)",
            host,
            port,
        )
        tcp_server.serve_forever()


def build_client() -> FastmailClient:
    load_env()
    base_url = os.environ.get("FASTMAIL_BASE_URL", "https://api.fastmail.com")
    username = os.environ.get("FASTMAIL_USERNAME", "local-user")
    app_password = os.environ.get("FASTMAIL_APP_PASSWORD", "local-app-password")
    token = os.environ.get("FASTMAIL_TOKEN")
    return FastmailClient(
        base_url=base_url,
        username=username,
        app_password=app_password,
        token=token or None,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Fastmail MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "tcp"),
        default=os.environ.get("MCP_TRANSPORT_MODE", "stdio"),
        help="Transport mode: stdio (default) or tcp",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_TCP_HOST", "0.0.0.0"),
        help="Host/interface to bind when using the TCP transport",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_TCP_PORT", "4000")),
        help="Port to bind when using the TCP transport",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args()
    client = build_client()
    server = FastmailMCPServer(client)
    register_all(server, client)
    if args.transport == "tcp":
        serve_tcp(server, host=args.host, port=args.port)
    else:
        logger.info("Fastmail MCP server ready for requests (stdio)")
        server.serve_forever()


if __name__ == "__main__":
    main()
