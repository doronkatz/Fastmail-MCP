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

## Linear Issue Workflow

When processing requests to review, plan, or implement Linear issues, always follow this workflow:

### 1. Mark Issue as In Progress
Use the Linear MCP integration to update the issue status to "In Progress" before beginning any work.

### 2. Create Feature Branch
Create a new feature branch following the naming convention:
```
feature/DOR-XXX-short-summary
```
Where:
- `DOR-XXX` is the Linear issue identifier (e.g., DOR-123)
- `short-summary` is a brief kebab-case description of the feature/fix

Example: `feature/DOR-456-add-search-filters`

### 3. Implement Changes
- Work on the feature/fix in the newly created branch
- Follow all existing coding standards and testing requirements
- Ensure all changes are properly tested and linted

### 4. Never Auto-Commit
**CRITICAL**: Never commit changes automatically. Always ask the human for review and approval before committing any changes. This includes:
- Individual commits during development
- Final commits before creating PRs
- Any git operations that modify the repository history

### 5. Human Approval Required
Before making any commits:
1. Summarize the changes made
2. Show the human what will be committed
3. Wait for explicit approval to proceed
4. Only commit after receiving clear confirmation

This workflow ensures proper Linear issue tracking, consistent branch naming, and maintains human oversight over all repository changes.

### 6. Pre-Commit Validation
**CRITICAL**: Before requesting human approval for any commits, always run the full validation pipeline:

1. **Build Check**: Ensure all code imports and runs without syntax errors
   ```bash
   python3 -c "import sys; sys.path.insert(0, 'src'); import fastmail_mcp"
   ```

2. **Unit Tests**: Run comprehensive test suite with minimum 80% coverage
   ```bash
   python3 -m pytest tests/ --cov=fastmail_mcp --cov-report=term-missing --cov-fail-under=80
   ```

3. **Code Quality**: Run linting and formatting checks
   ```bash
   ruff check src tests
   black --check src tests
   ```

4. **Integration Test**: Verify MCP server can start and register commands
   ```bash
   python3 -m fastmail_mcp.server --help
   ```

**No commits should be made without:**
- ✅ All tests passing
- ✅ Coverage ≥80% on new/modified code
- ✅ No linting errors
- ✅ Successful build verification

Only after ALL validation steps pass should you summarize changes and request human approval for commit.

## Security & Configuration Tips
Store real credentials in a local `.env` file (ignored by git). Ship only sanitized examples via `.env.example`, documenting `FASTMAIL_USERNAME`, `FASTMAIL_APP_PASSWORD`, `FASTMAIL_BASE_URL`, and optional sample overrides (`FASTMAIL_SAMPLE_DATA`, `FASTMAIL_CONTACT_SAMPLE_DATA`, `FASTMAIL_EVENT_SAMPLE_DATA`). Never log raw tokens or full message bodies; redact PII before checking fixtures into `assets/`. Rotate Fastmail app passwords used for local testing monthly and revoke them when debugging sessions finish.
