# Repository Guidelines

## Project Structure & Module Organization
Runtime code lives in `src/fastmail_mcp/`. Organize commands under `commands/`, long-lived API clients in `client/`, data models in `models/`, and shared helpers in `utils.py`. The MCP entry point is `server.py`, which wires the command registry and stdio loop. Store JSON fixtures or sample payloads in `assets/` (for example, `assets/messages_sample.json`). Documentation and release notes belong in `docs/`. Tests mirror their source modules under `tests/` (for instance, `tests/commands/test_messages.py` pairs with `src/fastmail_mcp/commands/messages.py`).

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` — create a clean environment.
- `pip install -r requirements.txt` — install tooling and runtime deps (`requests`, `pytest`, `ruff`, `black`).
- `ruff check src tests` — lint code; add `--fix` locally for quick wins.
- `pytest` — run the full suite (live smoke tests are skipped unless `FASTMAIL_LIVE_TESTS=1`).
- `python -m fastmail_mcp.server` — start the MCP server over stdio for manual ChatGPT runs.
- `python -m fastmail_mcp.cli verify` — confirm your `.env` Fastmail credentials work before attaching to ChatGPT.

## Coding Style & Naming Conventions
Target Python 3.11 semantics. Format with `black` (88 columns) and lint with `ruff`. Use four-space indentation, `snake_case` for functions/modules, and `PascalCase` for classes. Constants stay upper snake case (e.g., `FASTMAIL_BASE_URL`). Command identifiers follow kebab-case (`messages-list`). Keep docstrings focused on intent and add inline comments only when they clarify tricky logic.

## Testing Guidelines
All feature work needs pytest coverage. Reuse fixtures from `tests/fixtures/` and model tests after the source layout. Use descriptive test names (`test_transport_returns_sorted_messages`). Run `pytest --cov=fastmail_mcp --cov-report=term-missing` before opening a PR; aim for ≥85% coverage on new modules. Mark long-running network tests with `@pytest.mark.slow` so they stay opt-in.

## Commit & Pull Request Guidelines
Use Conventional Commits (`feat:`, `fix:`, `chore:`) and keep each commit targeted. PRs must include a short summary, linked task or issue, manual test notes, and screenshots or JSON samples when command output changes. Request review from another Fastmail MCP contributor before merging.

## Security & Configuration Tips
Store real credentials in a local `.env` file (ignored by git). Ship only sanitized examples via `.env.example`, documenting `FASTMAIL_USERNAME`, `FASTMAIL_APP_PASSWORD`, `FASTMAIL_BASE_URL`, and optional sample overrides (`FASTMAIL_SAMPLE_DATA`, `FASTMAIL_CONTACT_SAMPLE_DATA`, `FASTMAIL_EVENT_SAMPLE_DATA`). Never log raw tokens or full message bodies; redact PII before checking fixtures into `assets/`. Rotate Fastmail app passwords used for local testing monthly and revoke them when debugging sessions finish.
