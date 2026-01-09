# Changelog

## 1.0.0 - 2024-07-05
- Bootstrap Fastmail MCP server with live JMAP transport and fixture fallback
- Provide command registration for `messages-list`, `contacts-list`, and `events-list`
- Document environment handling with `.env`, ship sample data for local testing, and add CLI verification
- Add pytest coverage for client, transport, commands, and stdio server behavior (including slow live smoke test)
