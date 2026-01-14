# Fastmail MCP Tool Catalog

## Overview

This document defines the complete MCP tool surface for Fastmail integration, including schemas, query semantics, and example usage patterns. The tools are designed to provide comprehensive mail management capabilities while maintaining security through clear read/write operation distinctions.

## Tool Categories

### Read Operations (Always Available)
- `messages-list`: Basic message listing (legacy compatibility)
- `messages-search`: Advanced message search with filtering
- `messages-get`: Get detailed message information
- `mailboxes-list`: List mailboxes/folders

### Write Operations (Gated)
- `messages-send`: Send email messages (requires `FASTMAIL_ENABLE_WRITE_TOOLS=true`)

## Tool Specifications

### messages-list

**Description:** Return recent Fastmail messages for the authenticated account (legacy compatibility).

**Parameters:**
- `limit` (integer, optional): Number of messages to return (default: 10, max: 100)

**Response:**
```json
{
  "messages": [
    {
      "id": "string",
      "subject": "string", 
      "snippet": "string",
      "received_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 10
}
```

**Example Usage:**
```json
{"command": "messages-list", "params": {"limit": 5}}
```

### messages-search

**Description:** Search Fastmail messages with advanced filtering options. Supports filtering by sender, subject, date ranges, mailbox, read status, and attachments.

**Parameters:**
- `sender` (string, optional): Filter by sender email address
- `subject` (string, optional): Filter by subject text (partial match)
- `mailbox` (string, optional): Filter by mailbox ID
- `read` (boolean, optional): Filter by read status (true/false)
- `has_attachment` (boolean, optional): Filter by attachment presence
- `date_start` (string, optional): Start date filter (ISO format)
- `date_end` (string, optional): End date filter (ISO format)  
- `limit` (integer, optional): Number of results (default: 10, max: 100)
- `offset` (integer, optional): Pagination offset (default: 0)
- `sort_by` (string, optional): Sort field - "receivedAt", "sentAt", "subject", "from" (default: "receivedAt")
- `sort_ascending` (boolean, optional): Sort direction (default: false)

**Response:**
```json
{
  "messages": [
    {
      "id": "string",
      "subject": "string",
      "sender": "email@example.com",
      "snippet": "string", 
      "received_at": "2024-01-01T00:00:00Z",
      "read": true,
      "has_attachment": false,
      "mailbox": "mailbox_id"
    }
  ],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total": 150,
    "has_more": true
  }
}
```

**Example Usage:**
```json
{
  "command": "messages-search",
  "params": {
    "sender": "john@example.com",
    "read": false,
    "date_start": "2024-01-01T00:00:00Z",
    "limit": 20
  }
}
```

### messages-get

**Description:** Get detailed information for a specific message by ID.

**Parameters:**
- `message_id` (string, required): The message ID to retrieve
- `include_body` (boolean, optional): Include message body content (default: false)
- `include_headers` (boolean, optional): Include email headers (default: false)

**Response:**
```json
{
  "message": {
    "id": "string",
    "subject": "string",
    "sender": "email@example.com",
    "to": ["recipient@example.com"],
    "cc": ["cc@example.com"],
    "received_at": "2024-01-01T00:00:00Z",
    "sent_at": "2024-01-01T00:00:00Z",
    "body_text": "Plain text body (if requested)",
    "body_html": "<html>HTML body (if requested)</html>",
    "headers": {"Header-Name": "value"},
    "attachments": [
      {
        "name": "document.pdf",
        "size": 12345,
        "type": "application/pdf"
      }
    ]
  }
}
```

**Example Usage:**
```json
{
  "command": "messages-get",
  "params": {
    "message_id": "msg123",
    "include_body": true
  }
}
```

### mailboxes-list

**Description:** List available mailboxes/folders with unread and total counts.

**Parameters:**
- `limit` (integer, optional): Number of mailboxes to return (default: 50, max: 100)
- `offset` (integer, optional): Pagination offset (default: 0)

**Response:**
```json
{
  "mailboxes": [
    {
      "id": "string",
      "name": "Inbox",
      "parent_id": null,
      "unread_count": 5,
      "total_count": 150
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total": 10,
    "has_more": false
  }
}
```

**Example Usage:**
```json
{"command": "mailboxes-list", "params": {"limit": 10}}
```

### messages-send

**Description:** [WRITE] Send an email message. Requires `FASTMAIL_ENABLE_WRITE_TOOLS=true`.

**Parameters:**
- `to` (array[string], required): Recipient email addresses
- `subject` (string, required): Email subject
- `body_text` (string, optional): Plain text body
- `body_html` (string, optional): HTML body
- `cc` (array[string], optional): CC recipients
- `bcc` (array[string], optional): BCC recipients

**Note:** Either `body_text` or `body_html` is required.

**Response:**
```json
{
  "message_id": "string",
  "success": true,
  "note": "Email sending not yet implemented. Placeholder response only."
}
```

**Example Usage:**
```json
{
  "command": "messages-send",
  "params": {
    "to": ["recipient@example.com"],
    "subject": "Test Message",
    "body_text": "Hello, this is a test message."
  }
}
```

## Query Semantics and JMAP Mapping

### Filtering Logic

The MCP filtering system maps directly to JMAP filter objects:

| MCP Filter | JMAP Filter | Description |
|-----------|-------------|-------------|
| `sender` | `from` | Email address matching |
| `subject` | `subject` | Subject text search |
| `mailbox` | `inMailbox` | Mailbox ID filtering |
| `read` | `isUnread` | Read status (inverted) |
| `has_attachment` | `hasAttachment` | Attachment presence |
| `date_start` | `after` | Date range start |
| `date_end` | `before` | Date range end |

### Date Handling

- All dates use ISO 8601 format: `2024-01-01T00:00:00Z`
- Date ranges are inclusive of start date, exclusive of end date
- Invalid date formats return validation errors with troubleshooting guidance

### Pagination

- Uses limit/offset pagination pattern
- Maximum limit of 100 items per request
- Response includes `has_more` boolean for client convenience
- JMAP position-based pagination mapped to offset

## Prompt-to-Tool Mapping Examples

### Common Agent Tasks

**"Show me recent emails from John"**
```json
{
  "command": "messages-search",
  "params": {
    "sender": "john@example.com",
    "limit": 10
  }
}
```

**"Find unread emails from last week with attachments"**
```json
{
  "command": "messages-search", 
  "params": {
    "read": false,
    "has_attachment": true,
    "date_start": "2024-01-01T00:00:00Z",
    "date_end": "2024-01-08T00:00:00Z"
  }
}
```

**"Get the full content of message abc123"**
```json
{
  "command": "messages-get",
  "params": {
    "message_id": "abc123",
    "include_body": true,
    "include_headers": true
  }
}
```

**"List all my folders"**
```json
{"command": "mailboxes-list"}
```

**"Send a thank you email to the team"**
```json
{
  "command": "messages-send",
  "params": {
    "to": ["team@company.com"],
    "subject": "Thank you!",
    "body_text": "Thanks for all your hard work on the project."
  }
}
```

## Error Handling

All tools return structured error responses with troubleshooting guidance:

```json
{
  "error": {
    "error_type": "AuthenticationError",
    "message": "Authentication failed",
    "troubleshooting": "Check FASTMAIL_USERNAME and FASTMAIL_APP_PASSWORD in .env. Ensure app password is valid and not expired."
  }
}
```

### Common Error Types

- `AuthenticationError`: Invalid credentials
- `CapabilityError`: Missing JMAP capabilities
- `NetworkError`: Connection or service issues
- `ValidationError`: Invalid input parameters
- `PermissionDenied`: Write operations disabled

## Rate Limiting and Performance

- JMAP requests are batched where possible (query + get operations)
- Transport layer handles session management and credential caching
- Fallback to fixture data when live API unavailable
- Recommended limits: 10-50 items per request for optimal performance

## Security Considerations

- Read operations require only basic authentication
- Write operations gated by environment variable
- No sensitive data logged or exposed in fixtures
- App passwords recommended over OAuth for personal use
- Regular credential rotation advised

## Implementation Status

✅ **Implemented:**
- Complete schema definitions with type safety
- Advanced message searching with all filter types
- Pagination with limit/offset pattern
- Structured error responses with troubleshooting
- Environment-based write operation gating
- Comprehensive JMAP query mapping

⚠️ **Partial:**
- Email sending (placeholder implementation)

🔄 **Future Enhancements:**
- Full JMAP EmailSubmission integration
- Contacts and calendar tool expansion (pending JMAP token access)
- Real-time sync and change notifications
- Advanced search operators (AND/OR logic)