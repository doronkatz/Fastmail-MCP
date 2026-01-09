#!/usr/bin/env bash
set -euo pipefail

MODE=${MCP_TRANSPORT_MODE:-stdio}
HOST=${MCP_TCP_HOST:-0.0.0.0}
PORT=${MCP_TCP_PORT:-4000}

if [[ "$MODE" == "tcp" ]]; then
  echo "[entrypoint] Starting Fastmail MCP server in TCP mode on ${HOST}:${PORT}" >&2
  exec python -m fastmail_mcp.server --transport tcp --host "${HOST}" --port "${PORT}"
fi

echo "[entrypoint] Starting Fastmail MCP server in stdio mode" >&2
exec python -m fastmail_mcp.server --transport stdio
