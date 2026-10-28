import logging
from dataclasses import dataclass, field

from jsonschema import Draft202012Validator

from tracker_apps.ai_service.date_resolver import DateResolver
from tracker_apps.ai_service.exceptions import InvalidAnalysisOutput
from tracker_apps.ai_service.providers.base import AnalysisRequest
from tracker_apps.ai_service.schemas import ANALYSIS_SCHEMA
from tracker_apps.ai_service.text_utils import known_names, normalise
from tracker_apps.common.sanitizer import HtmlSanitizer

logger = logging.getLogger(__name__)
SCHEMA_VALIDATOR = Draft202012Validator(ANALYSIS_SCHEMA)
MIN_EVIDENCE_CHARS = 8
EVIDENCE_SECTIONS = ("decisions", "risks", "unanswered_questions")


@dataclass
class ValidationReport:
    """Counts only. No transcript or provider text ever goes in here."""

    dropped: dict[str, int] = field(default_factory=dict)
    owners_nulled: int = 0
    dates_nulled: int = 0

    @property
    def total_changes(self) -> int:
        return sum(self.dropped.values()) + self.owners_nulled + self.dates_nulled

    def drop(self, section: str) -> None:
        self.dropped[section] = self.dropped.get(section, 0) + 1


class AnalysisOutputValidator:
    """Two tiers. Structural problems reject the whole result; item-level problems drop or null just that item."""

    def __init__(self, request: AnalysisRequest) -> None:
        self.request = request
        self.transcript = normalise(request.transcript)
        self.names = known_names(request.participants, request.transcript)

    def validate(self, raw: object) -> tuple[dict, ValidationReport]:
        self.check_structure(raw)
        report = ValidationReport()
        cleaned = {
            "summary": self.clean_summary(raw["summary"]),
            "discussion_points": [point.strip() for point in raw["discussion_points"] if point.strip()],
            "action_items": self.clean_action_items(raw["action_items"], report),
        }
        for section in EVIDENCE_SECTIONS:
            cleaned[section] = self.clean_evidence_items(section, raw[section], report)
        self.reject_if_everything_dropped(raw, cleaned)
        self.log_report(report)
        return cleaned, report

    @staticmethod
    def check_structure(raw: object) -> None:
        errors = list(SCHEMA_VALIDATOR.iter_errors(raw))
        if errors:
            reasons = sorted({f"{error.json_path}:{error.validator}" for error in errors})
            raise InvalidAnalysisOutput(reasons)

    @staticmethod
    def clean_summary(summary: str) -> str:
        cleaned = HtmlSanitizer.clean(summary)
        if not cleaned:
            raise InvalidAnalysisOutput(["$.summary:empty_after_sanitising"])
        return cleaned

    def is_grounded(self, evidence: str) -> bool:
        normalised = normalise(evidence)
        return len(normalised) >= MIN_EVIDENCE_CHARS and normalised in self.transcript

    def clean_evidence_items(self, section: str, items: list[dict], report: ValidationReport) -> list[dict]:
        kept: list[dict] = []
        for item in items:
            if item["text"].strip() and self.is_grounded(item["evidence"]):
                kept.append({"text": item["text"].strip(), "evidence": item["evidence"].strip()})
            else:
                report.drop(section)
        return kept

    def clean_action_items(self, items: list[dict], report: ValidationReport) -> list[dict]:
        kept: list[dict] = []
        for item in items:
            if not item["description"].strip() or not self.is_grounded(item["evidence"]):
                report.drop("action_items")
                continue
            kept.append(
                {
                    "description": item["description"].strip(),
                    "owner": self.clean_owner(item["owner"], report),
                    "due_date_text": (item["due_date_text"] or "").strip() or None,
                    "due_date": self.clean_due_date(item, report),
                    "priority": item["priority"],
                    "evidence": item["evidence"].strip(),
                }
            )
        return kept

    def clean_owner(self, owner: str | None, report: ValidationReport) -> str | None:
        owner = (owner or "").strip()
        if not owner:
            return None
        if normalise(owner) in self.names:
            return owner
        report.owners_nulled += 1
        return None

    def clean_due_date(self, item: dict, report: ValidationReport) -> str | None:
        """Keep a date only if it is a real date that agrees with what was said."""
        if item["due_date"] is None:
            return None
        parsed = DateResolver.parse_iso(item["due_date"])
        text = (item["due_date_text"] or "").strip()
        if parsed is not None and (not text or DateResolver.resolve(text, self.request.meeting_date) == parsed):
            return item["due_date"]
        report.dates_nulled += 1
        return None

    @staticmethod
    def reject_if_everything_dropped(raw: dict, cleaned: dict) -> None:
        offered = len(raw["decisions"]) + len(raw["action_items"])
        kept = len(cleaned["decisions"]) + len(cleaned["action_items"])
        if offered > 0 and kept == 0:
            raise InvalidAnalysisOutput(["$:all_actions_and_decisions_dropped"])

    @staticmethod
    def log_report(report: ValidationReport) -> None:
        if report.total_changes:
            logger.warning(
                "Analysis output adjusted: dropped=%s owners_nulled=%d dates_nulled=%d",
                report.dropped,
                report.owners_nulled,
                report.dates_nulled,
            )
