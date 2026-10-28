from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class MeetingCreate:
    title: str
    meeting_date: date
    meeting_type: str
    transcript: str = field(repr=False)
    participants: list[str] = field(default_factory=list)
    notes: str = ""
    transcript_source: str = "text"
    transcript_filename: str | None = None
    created_at: datetime | None = None  # read-only: set by the database, never taken from a request
    updated_at: datetime | None = None  # read-only: refreshed on every save
