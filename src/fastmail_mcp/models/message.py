"""Data structures for Fastmail messages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass()
class Message:
    """Lightweight representation of the subset of fields the agent needs."""

    id: str
    subject: str
    snippet: str
    received_at: datetime

    @classmethod
    def from_json(cls, payload: Dict[str, Any]) -> "Message":
        received_at_raw = payload.get("received_at") or payload.get("receivedAt")
        if not received_at_raw:
            raise ValueError("Message payload missing received_at field")
        received_at = datetime.fromisoformat(received_at_raw)
        return cls(
            id=str(payload["id"]),
            subject=str(payload.get("subject", "")),
            snippet=str(payload.get("snippet", "")),
            received_at=received_at,
        )

    def to_summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "snippet": self.snippet,
            "received_at": self.received_at.isoformat(),
        }
