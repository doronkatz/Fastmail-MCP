# Fastmail JMAP Research Notes

## Purpose

Capture Fastmail JMAP endpoints, capabilities, and auth options to guide MCP
implementation and future planning. This is the source of truth for JMAP
behaviors and required permissions.

## Session Discovery

- Endpoint: `GET https://api.fastmail.com/.well-known/jmap`
- Auth: HTTP Basic using `FASTMAIL_USERNAME` and `FASTMAIL_APP_PASSWORD`
- Output: `apiUrl`, `primaryAccounts`, and capability listings.

Example response (trimmed):

```json
{
  "apiUrl": "https://api.fastmail.com/jmap/",
  "primaryAccounts": {
    "urn:ietf:params:jmap:mail": "acc_mail",
    "urn:ietf:params:jmap:contacts": "acc_contacts",
    "urn:ietf:params:jmap:calendars": "acc_calendar"
  }
}
```

## Capabilities and Account IDs

- Required capabilities for current read-only usage:
  - `urn:ietf:params:jmap:core`
  - `urn:ietf:params:jmap:mail`
  - `urn:ietf:params:jmap:contacts`
  - `urn:ietf:params:jmap:calendars`
- The `primaryAccounts` map yields the `accountId` per capability, which must be
  included in method calls.
- Optional (write): `urn:ietf:params:jmap:submission` for `EmailSubmission`.

## Mail APIs (Read)

Current MCP transport uses `Email/query` and `Email/get`:

```json
{
  "using": [
    "urn:ietf:params:jmap:core",
    "urn:ietf:params:jmap:mail"
  ],
  "methodCalls": [
    [
      "Email/query",
      {
        "accountId": "acc_mail",
        "limit": 10,
        "sort": [
          {
            "property": "receivedAt",
            "isAscending": false
          }
        ]
      },
      "a"
    ],
    [
      "Email/get",
      {
        "accountId": "acc_mail",
        "properties": [
          "id",
          "subject",
          "preview",
          "receivedAt"
        ],
        "#ids": {
          "resultOf": "a",
          "name": "Email/query",
          "path": "/ids"
        }
      },
      "b"
    ]
  ]
}
```

Minimal response shape:

```json
{
  "methodResponses": [
    [
      "Email/query",
      {
        "ids": ["m1"]
      },
      "a"
    ],
    [
      "Email/get",
      {
        "list": [
          {
            "id": "m1",
            "subject": "Hi",
            "preview": "Snippet",
            "receivedAt": "2024-02-02T00:00:00+00:00"
          }
        ]
      },
      "b"
    ]
  ]
}
```

## Mail APIs (Write, Optional)

If sending is required, investigate `EmailSubmission` (JMAP submission
capability) and whether Fastmail allows it via app passwords.

## Contacts APIs

Current MCP transport uses `Contact/query` + `Contact/get`:

```json
{
  "using": [
    "urn:ietf:params:jmap:core",
    "urn:ietf:params:jmap:contacts"
  ],
  "methodCalls": [
    [
      "Contact/query",
      {
        "accountId": "acc_contacts",
        "limit": 10,
        "sort": [
          {
            "property": "name",
            "isAscending": true
          }
        ]
      },
      "a"
    ],
    [
      "Contact/get",
      {
        "accountId": "acc_contacts",
        "properties": [
          "id",
          "name",
          "emails"
        ],
        "#ids": {
          "resultOf": "a",
          "name": "Contact/query",
          "path": "/ids"
        }
      },
      "b"
    ]
  ]
}
```

Minimal response shape:

```json
{
  "methodResponses": [
    [
      "Contact/get",
      {
        "list": [
          {
            "id": "c1",
            "name": "Ada",
            "emails": [
              {
                "value": "ada@example.com"
              }
            ]
          }
        ]
      },
      "b"
    ]
  ]
}
```

## Calendar APIs

Current MCP transport uses `CalendarEvent/query` + `CalendarEvent/get`:

```json
{
  "using": [
    "urn:ietf:params:jmap:core",
    "urn:ietf:params:jmap:calendars"
  ],
  "methodCalls": [
    [
      "CalendarEvent/query",
      {
        "accountId": "acc_calendar",
        "limit": 10,
        "sort": [
          {
            "property": "start",
            "isAscending": true
          }
        ]
      },
      "a"
    ],
    [
      "CalendarEvent/get",
      {
        "accountId": "acc_calendar",
        "properties": [
          "id",
          "title",
          "start",
          "end"
        ],
        "#ids": {
          "resultOf": "a",
          "name": "CalendarEvent/query",
          "path": "/ids"
        }
      },
      "b"
    ]
  ]
}
```

Minimal response shape:

```json
{
  "methodResponses": [
    [
      "CalendarEvent/get",
      {
        "list": [
          {
            "id": "e1",
            "title": "Standup",
            "start": "2024-07-02T09:00:00+00:00",
            "end": "2024-07-02T09:15:00+00:00"
          }
        ]
      },
      "b"
    ]
  ]
}
```

## Auth Options

### App Password (Recommended for Personal Use)

- Use HTTP Basic auth with `FASTMAIL_USERNAME` + `FASTMAIL_APP_PASSWORD`.
- Works for session discovery and JMAP method calls.
- No refresh token handling required; simplest for local MCP usage.
- Store credentials only in `.env` (never in repo); rotate regularly.

### OAuth2 (Fallback)

- Use `Authorization: Bearer <token>` for session discovery and JMAP calls.
- Preferred if app passwords are unavailable or policy requires delegated access.
- Scope names must be confirmed with Fastmail OAuth documentation.
- MCP support: set `FASTMAIL_TOKEN` in `.env` to send the bearer token.

## Required Permissions / Scopes

- JMAP capabilities required for this MCP:
  - core, mail, contacts, calendars (see capability URNs above)
- OAuth2 scopes (gap): confirm exact Fastmail scope strings for
  mail/contacts/calendar and whether submission requires an extra scope.

## Open Questions / Gaps

- Confirm Fastmail OAuth scope names and any special requirements.
- Validate whether `EmailSubmission` is allowed for app-password auth.
- Capture real `capabilities` payload from a live account to verify optional
  JMAP extensions Fastmail exposes.
- Current validation token only exposes mail capability; contacts/calendar are
  unavailable for this account.
