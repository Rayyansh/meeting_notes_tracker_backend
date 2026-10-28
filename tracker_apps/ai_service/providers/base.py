from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class AnalysisRequest:
    """Everything a provider may see. Nothing that identifies the user is ever added here."""

    transcript: str
    meeting_date: date
    meeting_type: str
    participants: tuple[str, ...]


class MeetingAnalysisProvider(ABC):
    """Plug-in point for analysis engines. `analyze` returns a dict shaped like schemas.ANALYSIS_SCHEMA.

    Providers are untrusted: the service validates every result before anything is saved.
    """

    name: str
    model: str

    @abstractmethod
    def analyze(self, request: AnalysisRequest) -> dict:
        raise NotImplementedError
