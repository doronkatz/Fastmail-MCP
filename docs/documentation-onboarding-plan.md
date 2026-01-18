# Documentation and Onboarding Plan (Mail-only)

## Purpose

Define the documentation structure needed to onboard a personal user, configure
Fastmail auth, and use the MCP tools safely. Contacts and calendar remain out
of scope until Fastmail exposes JMAP tokens for them.

## Scope

In:
- README structure and quickstart steps.
- Auth setup walkthrough and troubleshooting.
- MCP tool reference and examples (mail-only).
- Operational notes (logging, cache, token revocation).

Out:
- Contacts/calendar documentation.
- Marketing or public-facing docs.

## Doc Set and Ownership

Primary docs:
- `README.md`: user-facing onboarding and quickstart.
- `docs/mcp-tool-catalog.md`: detailed tool reference.
- `docs/system-architecture-deployment-plan.md`: architecture and deployment.
- `docs/security-privacy-plan.md`: data handling, secrets, redaction.
- `docs/testing-strategy-mock-harness-plan.md`: test guidance (internal).

## README Outline (Required Sections)

1. **Overview**
   - What Fastmail MCP does (mail-only).
   - Read-only by default; write tools gated.

2. **Quickstart (Local)**
   - Create venv, install requirements.
   - Copy `.env.example` -> `.env` and set credentials.
   - Run `python -m fastmail_mcp.cli verify`.
   - Start server: `python -m fastmail_mcp.server`.

3. **Authentication Setup**
   - App password (recommended) vs OAuth token.
   - Where secrets live (local `.env`, not committed).
   - Troubleshooting: invalid credentials, missing capability warnings.

4. **Tool Usage (Mail-only)**
   - Link to `docs/mcp-tool-catalog.md`.
   - Include 1-2 minimal examples (see below).
   - Explicitly note `FASTMAIL_ENABLE_WRITE_TOOLS=true` for sending.

5. **Data Storage and Retention**
   - Cache location and defaults (90 days or 10,000 messages, 500 MB).
   - Cache opt-out and metadata-only mode.
   - Reference `docs/mail-data-model-sync-strategy.md`.

6. **Logging and Privacy**
   - Redaction defaults and restricted fields.
   - Link to `docs/security-privacy-plan.md`.

7. **Troubleshooting**
   - Common auth errors (401/403), token revocation.
   - Missing JMAP capabilities.
   - Live test opt-in with `FASTMAIL_LIVE_TESTS=1`.

8. **Deployment Runbooks**
   - Local runbook (venv).
   - Azure runbook (container with secrets injected).

## Sample Configuration Snippet

Use the `.env.example` structure with placeholders:

```bash
FASTMAIL_USERNAME=your.name@fastmail.com
FASTMAIL_APP_PASSWORD=app-specific-password
# Optional bearer token (overrides username/app password)
FASTMAIL_TOKEN=
FASTMAIL_BASE_URL=https://api.fastmail.com
FASTMAIL_SAMPLE_DATA=assets/messages_sample.json
FASTMAIL_CONTACT_SAMPLE_DATA=assets/contacts_sample.json
FASTMAIL_EVENT_SAMPLE_DATA=assets/events_sample.json
```

## Example Prompts and Expected Outputs

Minimal MCP request example (`messages-list`):

```json
{"command": "messages-list", "params": {"limit": 3}}
```

Expected response shape (sample):

```json
{
  "command": "messages-list",
  "result": {
    "messages": [
      {
        "id": "msg_123",
        "subject": "Welcome",
        "snippet": "Hello",
        "received_at": "2024-01-01T00:00:00Z"
      }
    ],
    "count": 1
  }
}
```

Write tool example (opt-in):

```json
{
  "command": "messages-send",
  "params": {
    "to": ["recipient@example.com"],
    "subject": "Hello",
    "body_text": "Hi from Fastmail MCP"
  }
}
```

Note: This requires `FASTMAIL_ENABLE_WRITE_TOOLS=true`.

## Tool Reference Plan (Mail-only)

Ensure the tool catalog includes:
- `messages-list`, `messages-search`, `messages-get`, `mailboxes-list`.
- `messages-send` with explicit gating language and warning about opt-in writes.
- Request/response examples and field descriptions.

## Operational Notes

- **Logging:** redact auth headers, tokens, message bodies, and PII by default.
- **Cache:** default SQLite cache with retention limits; allow cache-off mode.
- **Token revocation:** rotate app passwords monthly or on suspected exposure.
- **Safe defaults:** read-only tools enabled; write tools require explicit flag.

## Local Runbook (Outline)

1. Create venv and install requirements.
2. Copy `.env.example` and set credentials.
3. Run `python -m fastmail_mcp.cli verify`.
4. Start server with stdio transport.
5. Test with a simple MCP request.

## Azure Runbook (Outline)

1. Build/push container image.
2. Store secrets in Key Vault or Container Apps secrets.
3. Inject env vars at runtime (no secrets in image).
4. Disable TCP ingress unless required; restrict network access.
5. Verify logs are redacted and routed to platform logging.

## Open Questions

- Should README include a short security checklist or link only to the plan?
- Do we want a dedicated "cache-off" quickstart step?
- Should we publish a minimal "tools quick reference" table in README?
