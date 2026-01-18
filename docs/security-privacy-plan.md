# Security and Privacy Plan (Mail-only)

## Purpose

Define security and privacy requirements for handling personal mail data in the
Fastmail MCP server. Contacts and calendar remain out of scope until Fastmail
exposes a JMAP token for them.

## Scope

In:
- Threat model for local and Azure deployments.
- Secrets storage and rotation strategy.
- Data retention, cache encryption, and opt-out settings.
- Logging and redaction standards.

Out:
- Contacts/calendar data handling.
- Enterprise compliance programs (SOC2, HIPAA, etc.).

## Threat Model

### Assets

- Fastmail credentials (app password or OAuth token).
- Mail metadata (subject, preview, headers, mailbox names).
- Mail body content and attachments (if ever fetched).
- Local cache contents (SQLite).
- Logs and crash reports.

### Trust Boundaries

- Local host filesystem and process memory.
- MCP client and stdio/TCP transport.
- Fastmail JMAP API over HTTPS.
- Container runtime (Azure) and its secret injection path.

### Key Risks and Mitigations

| Risk | Vector | Impact | Mitigation |
| --- | --- | --- | --- |
| Credential leakage | `.env`, logs, crash dumps, shell history | Account compromise | Store secrets in keychain or managed secret store, redact logs, avoid echoing envs, short rotation cadence. |
| PII leakage in logs | Debug logging of payloads | Privacy breach | Default redaction of headers/bodies/addresses, log only counts and IDs. |
| Cache exfiltration | Local disk compromise, container volume copy | Privacy breach | Cache opt-out, encrypt at rest (FileVault or managed disks), limit retention. |
| MITM or TLS downgrade | Insecure network | Token and data theft | Enforce HTTPS, verify TLS by default, avoid custom CA unless required. |
| Over-collection | Fetching bodies/attachments unnecessarily | Unneeded sensitive data | Default to metadata-only, only fetch body on explicit request. |
| Unauthorized client access (Azure) | Exposed TCP, weak network controls | Data exposure | Disable TCP by default, restrict ingress, require auth in front of TCP bridge. |

## Secrets Storage and Rotation

### Storage recommendations

Local:
- Prefer OS keychain for long-lived credentials.
- Allow `.env` for development only; ensure `.env` is git-ignored.
- Never write credentials to `assets/` or log output.

Azure:
- Store secrets in Azure Key Vault or Container Apps secrets.
- Inject secrets as environment variables at runtime (no secrets baked into
  image or config repo).
- Use least-privilege service identities where possible.

### Rotation strategy

- App passwords: rotate monthly or after any suspected exposure.
- OAuth tokens: rely on provider rotation; refresh tokens must never be logged.
- On startup, fail fast if credentials are missing or malformed.
- After rotation, invalidate local caches if they include token-derived keys.

## Data Retention and Cache Policy

### Default retention

- Cache only metadata by default (no bodies or attachments).
- Retain at most 90 days or 10,000 messages (whichever comes first).
- Evict oldest entries when limits are exceeded.

### Opt-out and minimal modes

- Support cache-off mode for zero local storage (live API calls only).
- Support metadata-only mode even when cache is enabled.
- Avoid storing raw message bodies in cache unless explicitly requested.

### Encryption at rest

- Local: rely on full-disk encryption (e.g., FileVault) as baseline.
- Azure: use encrypted disks/volumes; avoid persistent volumes unless required.
- If a portable cache is introduced, require encryption and a user-supplied
  passphrase.

## Logging and Redaction Standards

### Allowed log data (default)

- Command name, duration, status, and counts.
- Mailbox IDs or message IDs only when necessary for debugging.

### Redaction rules

- Remove `Authorization`, `Proxy-Authorization`, and Basic auth headers.
- Strip `FASTMAIL_APP_PASSWORD`, `FASTMAIL_TOKEN`, and any bearer tokens.
- Redact message bodies, MIME payloads, and attachment contents.
- Redact email addresses and names; keep domains only if needed.
- Truncate subjects/previews to a short snippet if logged at all.

### Logging levels

- INFO: command summary only.
- DEBUG: sanitized request/response metadata (no payloads, no PII).
- ERROR: include stack trace with all sensitive values redacted.

## Security Checklist

- [ ] Secrets are loaded from keychain/managed store, not from repo files.
- [ ] `.env` remains git-ignored and not checked into commits.
- [ ] Logging defaults to redacted output (headers, bodies, addresses removed).
- [ ] Cache is optional and metadata-only by default.
- [ ] Retention limits and eviction are enforced.
- [ ] Azure deployments restrict network ingress and do not expose TCP by default.

## Open Questions

- Should cache encryption be mandatory for any non-local deployment?
- Do we want a dedicated "safe mode" flag that disables all logging of IDs?
- How should we document approved third-party log sinks (Sentry, Azure Monitor)?
