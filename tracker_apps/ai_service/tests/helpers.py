import copy
from datetime import date
from pathlib import Path

from tracker_apps.ai_service.providers.base import AnalysisRequest, MeetingAnalysisProvider
from tracker_apps.ai_service.providers.mock import MockProvider

FIXTURE = Path(__file__).parent / "fixtures" / "sample_transcript.txt"
SAMPLE_TRANSCRIPT = FIXTURE.read_text(encoding="utf-8")
SAMPLE_DATE = date(2026, 7, 28)  # a Tuesday
SAMPLE_PARTICIPANTS = (
    "Maria — Client Founder",
    "James — Client Operations Manager",
    "Neha — Zignuts Business Analyst",
    "Arjun — Zignuts Technical Lead",
    "Riya — Zignuts UI/UX Designer",
)


def sample_request() -> AnalysisRequest:
    return AnalysisRequest(SAMPLE_TRANSCRIPT, SAMPLE_DATE, "Requirement Discussion", SAMPLE_PARTICIPANTS)


def mock_output(request: AnalysisRequest | None = None) -> dict:
    return MockProvider().analyze(request or sample_request())


class FakeProvider(MeetingAnalysisProvider):
    """Test double: returns a canned result or raises; records the requests it received."""

    name = "fake"
    model = "fake-1"

    def __init__(self, result: object = None, error: Exception | None = None) -> None:
        self.result, self.error, self.requests = result, error, []

    def analyze(self, request: AnalysisRequest) -> dict:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return copy.deepcopy(self.result)
