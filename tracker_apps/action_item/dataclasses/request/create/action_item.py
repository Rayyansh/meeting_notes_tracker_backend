from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class ActionItemCreate:
    meeting_id: int
    description: str
    owner_name: str = ""
    due_date: date | None = None
    due_date_text: str = ""
    priority: str = "Medium"
    status: str = "Open"
    created_at: datetime | None = None  # read-only
    updated_at: datetime | None = None  # read-only
