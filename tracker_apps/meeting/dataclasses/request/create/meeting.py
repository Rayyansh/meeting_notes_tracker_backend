from dataclasses import dataclass, field
from datetime import date


@dataclass
class MeetingCreate:
    title: str
    meeting_date: date
    meeting_type: str
    transcript: str = field(repr=False)
    participants: list[str] = field(default_factory=list)
    notes: str = ""
