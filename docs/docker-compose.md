# Docker Compose Integration

This repository ships a Docker image that runs the Fastmail MCP server over stdio. The `docker-compose.yml` definition streamlines building the image and wiring environment variables for local credentials.

## Prerequisites

1. Copy `.env.example` to `.env` and populate it with your Fastmail app password and any sample-data overrides.
2. Install Docker Desktop (or another engine) and ensure `docker compose` is available in your shell.

## Build the image

```bash
docker compose build fastmail-mcp
```

This compiles a Python 3.11 runtime layer, installs `requirements.txt`, and
ships an entrypoint script that can run either over stdio (default) or via a TCP
bridge.

## Run the MCP server

Use `docker compose run` so the container exits cleanly when the requesting client finishes:

```bash
docker compose run --rm -T fastmail-mcp
```

The `-T` flag disables pseudo-TTY allocation, which keeps JSON-over-stdio payloads intact. You can still pipe requests directly:

```bash
echo '{"command": "messages-list"}' | docker compose run --rm -T fastmail-mcp
```

## Run as a TCP service

If you need to expose the MCP server over the network (for example on a remote
host), use the dedicated `fastmail-mcp-tcp` service. The container switches its
entrypoint to TCP mode, binding to the port defined by `MCP_TCP_PORT`
(defaults to `4000`).

```bash
MCP_TCP_PORT=4501 docker compose up fastmail-mcp-tcp
```

The service publishes the port so clients can connect with a TCP transport.
When running behind a firewall or reverse proxy, forward the chosen port to the
host running Docker. Set `MCP_TCP_HOST` if you need to bind to a specific
interface (defaults to `0.0.0.0`).

## Configuring MCP-aware clients

Many MCP clients let you register stdio servers in a JSON manifest. Point the command at `docker compose run --rm -T fastmail-mcp` so the container boots on demand. Replace the placeholder credentials below with your own secrets (or omit them if you rely on the `.env` loaded by Docker Compose).

### Cursor (`~/.cursor/mcp.json`)

```json
{
  "version": 1,
  "mcpServers": {
    "fastmail": {
      "command": "docker",
      "args": ["compose", "run", "--rm", "-T", "fastmail-mcp"],
      "env": {
        "FASTMAIL_USERNAME": "you@example.com",
        "FASTMAIL_APP_PASSWORD": "app-password",
        "FASTMAIL_BASE_URL": "https://api.fastmail.com"
      }
    }
  }
}
```

### Warp terminal (`~/.warp/workflows/mcp.json`)

```json
{
  "version": 1,
  "clients": {
    "fastmail": {
      "transport": {
        "type": "stdio",
        "command": "docker",
        "args": [
          "compose",
          "--project-directory",
          "/absolute/path/to/Fastmail-MCP",
          "run",
          "--rm",
          "-T",
          "fastmail-mcp"
        ]
      },
      "env": {
        "FASTMAIL_USERNAME": "you@example.com",
        "FASTMAIL_APP_PASSWORD": "app-password"
      }
    }
  }
}
```

The explicit `--project-directory` flag tells Docker where to find
`docker-compose.yml`. Adjust the path above to match the Fastmail MCP clone
on your machine.

If a client already sources environment variables from the host (for example by reading the same `.env`), you can drop the `env` block altogether.

## Debugging tips

- Run `docker compose logs fastmail-mcp` to inspect the most recent container output.
- Use `docker compose run --rm -T fastmail-mcp python -m fastmail_mcp.cli verify` to confirm credentials from inside the container.
- If you update dependencies, rebuild with `docker compose build --no-cache fastmail-mcp`.
