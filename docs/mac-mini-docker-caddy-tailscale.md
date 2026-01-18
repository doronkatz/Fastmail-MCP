# Mac mini deployment (Docker + Caddy + Tailscale)

## Overview

Run the Fastmail MCP server on a Mac mini in Docker, expose the TCP transport
through a TLS-terminating Caddy proxy, and restrict access to Tailnet clients
via Tailscale. The MCP TCP transport is raw JSON lines (not HTTP), so Caddy
must use a TCP-capable configuration (layer4 plugin).

## Prerequisites

- macOS on the Mac mini with sleep disabled for always-on access.
- Docker Desktop or Colima installed and running.
- Tailscale installed and logged in on the Mac mini.
- Caddy installed with the layer4 plugin (tcp proxy support).

## 1) Configure environment

Copy `.env.example` to `.env` and populate credentials. Keep `.env` local and
never commit it.

```bash
cp .env.example .env
```

## 2) Build and run the MCP container (TCP)

The `fastmail-mcp-tcp` service starts the TCP transport and includes a restart
policy. A named volume is mounted at `/app/data` for any future cache or
exports.

```bash
docker compose build fastmail-mcp-tcp
docker compose up -d fastmail-mcp-tcp
```

Default port: `4000` (override with `MCP_TCP_PORT`).

## 3) Generate a Tailnet TLS certificate

Use Tailscale to mint a cert for the Mac mini hostname:

```bash
sudo tailscale cert mac-mini.tailnet.ts.net
```

Copy the generated cert/key to the path referenced in
`docker/caddy/Caddyfile` (example uses `/etc/caddy/certs`).

## 4) Configure Caddy (TCP + TLS)

Use the sample Caddyfile for layer4 TCP proxying:

- `docker/caddy/Caddyfile`

This terminates TLS and proxies TCP to the MCP port. If you run Caddy in a
container, mount the certs and Caddyfile into the container. If you run Caddy
on the host, update the upstream target to `127.0.0.1:4000` and ensure the
cert paths are accessible.

## 5) Tailscale setup guidance

Recommended settings:

- Tag the Mac mini device, for example `tag:mcp`.
- Restrict access to the tag in tailnet ACLs.
- Do not enable Tailscale Funnel unless explicitly required.

Example ACL snippet:

```json
{
  "tagOwners": {"tag:mcp": ["autogroup:admin"]},
  "acls": [
    {"action": "accept", "src": ["group:admins"], "dst": ["tag:mcp:443"]}
  ]
}
```

## 6) Validate from a second Tailnet device

Use `nc` or a simple MCP client to verify:

```bash
printf '{"command": "messages-list", "params": {"limit": 1}}\n' \
  | nc mac-mini.tailnet.ts.net 443
```

If TLS is required end-to-end, use `openssl s_client` and paste the JSON line
request after the connection is established.

## Operational notes

### Logs

- MCP container logs: `docker compose logs -f fastmail-mcp-tcp`
- Caddy logs: `caddy logs` (host) or `docker logs caddy` (container)

### Updates

1. Pull latest changes and rebuild the image.
2. Restart the MCP container.
3. Validate with a test request from a Tailnet client.

```bash
git pull
docker compose build fastmail-mcp-tcp
docker compose up -d fastmail-mcp-tcp
```

### Rollback

- Stop the updated container and re-run the prior image tag.
- Keep the previous Docker image in case rollback is needed.

### Backups

- Store `.env` securely (password manager or encrypted vault).
- Backup any data stored in `fastmail-mcp-data` if used.

## Security checklist

- [ ] `.env` is local-only and not committed.
- [ ] Caddy listens only on Tailnet-facing ports.
- [ ] Tailscale ACLs restrict access to the MCP port.
- [ ] `FASTMAIL_ENABLE_WRITE_TOOLS` is unset unless needed.
- [ ] macOS sleep is disabled to keep the service available.
