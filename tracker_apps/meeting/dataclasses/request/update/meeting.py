from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class MeetingUpdate:
    """None means "not provided"; every updatable field is non-nullable."""

    meeting_id: int
    title: str | None = None
    meeting_date: date | None = None
    meeting_type: str | None = None
    participants: list[str] | None = None
    transcript: str | None = field(default=None, repr=False)
    notes: str | None = None
    reset_analysis: bool = False
    transcript_source: str = "text"
    transcript_filename: str | None = None
    created_at: datetime | None = None  # read-only: set by the database, never taken from a request
    updated_at: datetime | None = None  # read-only: refreshed on every save
