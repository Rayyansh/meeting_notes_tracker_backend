from dataclasses import dataclass
from datetime import datetime


@dataclass
class AnalysisUpdate:
    meeting_id: int
    summary: str
    created_at: datetime | None = None  # read-only
    updated_at: datetime | None = None  # read-only
