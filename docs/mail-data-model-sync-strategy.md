# Mail Data Model and Sync/Cache Strategy

## Purpose

Define internal mail data models, mapping rules to JMAP, and a caching/sync
strategy that keeps queries fast while minimizing API calls. Contacts and
calendar are deferred until Fastmail exposes JMAP tokens for them.

## Goals and Non-goals

Goals:
- Fast, local queries for common mail views (recent mail, inbox, unread).
- Minimal API calls by relying on JMAP state changes.
- Clear mapping between JMAP fields and internal schema.

Non-goals:
- Contacts/calendar models.
- Full-text search implementation (only interface needs).
- Multi-account synchronization (but schema should be extensible).

## Data Model

### Email (internal)

Primary key: `email.id` (JMAP `Email/id`).

Core fields:
- `id` (string, required)
- `thread_id` (string, required; JMAP `threadId`)
- `mailbox_ids` (many-to-many; JMAP `mailboxIds`)
- `subject` (string, default empty)
- `preview` (string, default empty)
- `from_` / `to` / `cc` / `bcc` / `reply_to` (list of addresses)
- `sent_at` (datetime, optional; JMAP `sentAt`)
- `received_at` (datetime, required; JMAP `receivedAt`)
- `size` (int, optional; JMAP `size`)
- `has_attachment` (bool, optional; JMAP `hasAttachment`)
- `keywords` (set of strings; JMAP `keywords`)
- `message_id` (string, optional; JMAP `messageId`)
- `in_reply_to` (list of strings, optional; JMAP `inReplyTo`)

Address shape (stored as JSON array):
- `name` (string, optional)
- `email` (string, required; JMAP `email`)

Storage notes:
- Message bodies are not cached by default; only `preview` is stored.
- Attachments are stored as metadata only (name, type, size, blob_id).
- Bodies or attachments can be fetched on-demand and cached if needed later.

### Mailbox (internal)

Primary key: `mailbox.id` (JMAP `Mailbox/id`).

Fields:
- `id` (string, required)
- `name` (string, required)
- `role` (string, optional; inbox, archive, trash, etc.)
- `parent_id` (string, optional)
- `sort_order` (int, optional)
- `total_emails` (int, optional)
- `unread_emails` (int, optional)
- `is_subscribed` (bool, optional)
- `my_rights` (json, optional)

### Sync metadata

Store per-account state to drive incremental sync:
- `email_state` (string, required; from `Email/get`)
- `mailbox_state` (string, required; from `Mailbox/get`)
- `last_sync_at` (datetime)
- `cache_version` (string) and `account_signature` (string)

## JMAP Mapping Rules

### Email mapping

| Internal field     | JMAP property   | Notes |
| --- | --- | --- |
| `id` | `id` | String copy |
| `thread_id` | `threadId` | String copy |
| `mailbox_ids` | `mailboxIds` | Map keys become join table rows |
| `subject` | `subject` | Default empty |
| `preview` | `preview` | Default empty |
| `from_` | `from` | Map to list of `{name,email}` |
| `to` | `to` | Same as `from` |
| `cc` | `cc` | Same as `from` |
| `bcc` | `bcc` | Same as `from` |
| `reply_to` | `replyTo` | Same as `from` |
| `sent_at` | `sentAt` | ISO-8601 -> datetime |
| `received_at` | `receivedAt` | ISO-8601 -> datetime |
| `size` | `size` | Integer |
| `has_attachment` | `hasAttachment` | Boolean |
| `keywords` | `keywords` | Keys of map become set |
| `message_id` | `messageId` | String |
| `in_reply_to` | `inReplyTo` | List of strings |
| `attachments` | `attachments` | Store metadata only |

### Mailbox mapping

| Internal field     | JMAP property | Notes |
| --- | --- | --- |
| `id` | `id` | String copy |
| `name` | `name` | String copy |
| `role` | `role` | Optional |
| `parent_id` | `parentId` | Optional |
| `sort_order` | `sortOrder` | Optional |
| `total_emails` | `totalEmails` | Optional |
| `unread_emails` | `unreadEmails` | Optional |
| `is_subscribed` | `isSubscribed` | Optional |
| `my_rights` | `myRights` | JSON |

## Cache Strategy

### Storage choice

Use SQLite for the local cache:
- Built-in on macOS and available in Python stdlib.
- Supports indexed queries and partial updates.
- Safer than ad-hoc JSON files for concurrent access.

Proposed location:
- Default: `~/.fastmail-mcp/cache.sqlite`
- Override via `FASTMAIL_CACHE_DIR` or `FASTMAIL_CACHE_PATH`.

### Indexing

Suggested indexes for fast queries:
- `emails(received_at DESC)`
- `emails(thread_id)`
- `email_mailboxes(mailbox_id, email_id)`
- `emails(subject)` (prefix searches only; full-text is out-of-scope)

### Retention and size limits

Defaults (configurable):
- Keep last 90 days of mail or last 10,000 messages.
- Max cache size 500 MB (evict oldest first).
- Evict on startup and after sync if above thresholds.

### Invalidation

Invalidate and rebuild cache when:
- Account signature changes (base URL, username, account id).
- Cache schema version changes.
- User explicitly opts out of caching.

### Privacy

Support a cache-off mode that bypasses SQLite and uses live calls only.
Also support a metadata-only mode (no body/attachments).

## Sync Strategy

### Initial sync

1. Fetch mailboxes via `Mailbox/get` and store `mailbox_state`.
2. Warm cache with recent mail:
   - Run `Email/query` sorted by `receivedAt` descending.
   - Page by `position` + `limit` until the retention window is filled.
3. Fetch message details in batches via `Email/get`.
4. Store `email_state` from the response.

### Incremental sync

1. If `last_sync_at` is older than a short threshold (e.g. 2-5 minutes),
   run `Email/changes` with `sinceState = email_state`.
2. For `updated` IDs, call `Email/get` and upsert.
3. For `destroyed` IDs, delete rows and join entries.
4. Update `email_state` and `last_sync_at`.
5. Run `Mailbox/changes` similarly and update mailbox records.

### Pagination and rate limits

- Cap `Email/get` batches at ~100-200 IDs.
- Respect `maxChanges` and loop while `hasMoreChanges` is true.
- If errors occur, fall back to live fetch for the current query.

### Expected API usage

Typical incremental sync:
- 1x `Email/changes`
- 1x `Email/get` (only for changed IDs)
- 1x `Mailbox/changes` (if mailbox data is requested)

## Performance Targets

Assuming a warm cache on local SSD:
- List recent messages (limit 50): < 150 ms.
- Inbox + unread filter (limit 50): < 200 ms.
- Mailbox list + counts: < 50 ms.
- Fetch message summary by id: < 20 ms.
- Incremental sync with < 200 changes: < 2 seconds.

## Open Questions

- Do we need thread-level summaries (count, last received)?
- Should we cache bodies for the last N messages by default?
- Which config defaults should be exposed in CLI vs env vars?
