# Fastmail MCP

Fastmail MCP is a Model Context Protocol (MCP) server that exposes Fastmail
capabilities as commands over stdio, making it easy to integrate Fastmail data
into LLM workflows and tooling.

## Highlights

- MCP server entry point for ChatGPT/LLM integrations.
- Command-oriented layout for messages, contacts, events, and more.
- Sample payloads and fixtures for local development.

## Project Layout

- `src/fastmail_mcp/` runtime package
- `src/fastmail_mcp/server.py` MCP server entry point
- `src/fastmail_mcp/commands/` command modules
- `src/fastmail_mcp/client/` long-lived API clients
- `src/fastmail_mcp/models/` data models
- `src/fastmail_mcp/utils.py` shared helpers
- `assets/` sample JSON payloads
- `docs/` documentation and release notes
- `tests/` pytest suite mirroring source layout

## Getting Started

### Prerequisites

- Python 3.11
- Fastmail account and app password

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file (not committed) with your Fastmail credentials:

```
FASTMAIL_USERNAME=you@example.com
FASTMAIL_APP_PASSWORD=your-app-password
FASTMAIL_BASE_URL=https://api.fastmail.com
```

Optional sample overrides for local development:

```
FASTMAIL_SAMPLE_DATA=assets/messages_sample.json
FASTMAIL_CONTACT_SAMPLE_DATA=assets/contacts_sample.json
FASTMAIL_EVENT_SAMPLE_DATA=assets/events_sample.json
```

### Verify Credentials

```bash
python -m fastmail_mcp.cli verify
```

### Run the MCP Server

```bash
python -m fastmail_mcp.server
```

### Tests and Quality Checks

```bash
ruff check src tests
black --check src tests
pytest
```

## Contributing

1. Create a feature branch from `main`.
2. Keep changes focused and aligned with the existing structure.
3. Add or update tests for new behavior.
4. Run linting and the full test suite before requesting review.
5. Use Conventional Commits (`feat:`, `fix:`, `chore:`) when committing.

If your change modifies command output, include updated samples or screenshots in
the PR.

## Troubleshooting

- Ensure `.env` is present and credentials are valid.
- Use `python -m fastmail_mcp.cli verify` to validate auth quickly.
- Live tests are skipped unless `FASTMAIL_LIVE_TESTS=1` is set.
