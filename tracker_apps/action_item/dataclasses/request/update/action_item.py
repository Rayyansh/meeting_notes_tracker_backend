from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class ActionItemUpdate:
    """`provided` lists the fields the client actually sent, so an explicit null due_date (clear it) differs from "not sent"."""

    action_item_id: int
    description: str | None = None
    owner_name: str | None = None
    due_date: date | None = None
    due_date_text: str | None = None
    priority: str | None = None
    status: str | None = None
    provided: frozenset[str] = field(default_factory=frozenset)
    created_at: datetime | None = None  # read-only
    updated_at: datetime | None = None  # read-only
