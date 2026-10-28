from dataclasses import dataclass, field
from datetime import date


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
