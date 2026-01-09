"""Data structures for Fastmail calendar events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass
class CalendarEvent:
    id: str
    title: str
    starts_at: datetime
    ends_at: datetime | None

    @classmethod
    def from_json(cls, payload: Dict[str, Any]) -> "CalendarEvent":
        start_raw = payload.get("start") or payload.get("startAt")
        if not start_raw:
            raise ValueError("Calendar event payload missing start timestamp")
        end_raw = payload.get("end") or payload.get("endAt")
        return cls(
            id=str(payload.get("id", "")),
            title=str(payload.get("title", "")),
            starts_at=_parse_timestamp(start_raw),
            ends_at=_parse_optional_timestamp(end_raw),
        )

    def to_summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "starts_at": self.starts_at.isoformat(),
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
        }


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _parse_optional_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return _parse_timestamp(value)
