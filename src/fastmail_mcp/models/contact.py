"""Data structures for Fastmail contacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable


@dataclass
class Contact:
    id: str
    display_name: str
    email: str | None

    @classmethod
    def from_json(cls, payload: Dict[str, Any]) -> "Contact":
        emails = payload.get("emails") or []
        primary_email = _first_email(emails)
        return cls(
            id=str(payload.get("id", "")),
            display_name=str(payload.get("name", "")),
            email=primary_email,
        )

    def to_summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "email": self.email,
        }


def _first_email(entries: Iterable[Dict[str, Any]]) -> str | None:
    for entry in entries:
        value = entry.get("value")
        if value:
            return str(value)
    return None
