import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status

from tracker.config import Configurations
from tracker.constants import Constants
from tracker_apps.action_item.choices import Priority, Source
from tracker_apps.action_item.models.action_item import ActionItem
from tracker_apps.ai_service.exceptions import InvalidAnalysisOutput, ProviderConfigError, ProviderError
from tracker_apps.ai_service.providers.base import AnalysisRequest, MeetingAnalysisProvider
from tracker_apps.ai_service.providers.registry import get_provider
from tracker_apps.ai_service.validators import AnalysisOutputValidator
from tracker_apps.common.exceptions.http_errors import ConflictErrors, UpstreamErrors
from tracker_apps.common.exceptions.validation_errors import ValidationErrors
from tracker_apps.meeting.choices import AnalysisStatus
from tracker_apps.meeting.models.meeting import Meeting
from tracker_apps.meeting.models.meeting_analysis import MeetingAnalysis

logger = logging.getLogger(__name__)

FAILURE_HTTP_STATUS: dict[str, int] = {
    Constants.ai_error_timeout: status.HTTP_504_GATEWAY_TIMEOUT,
    Constants.ai_error_rate_limited: status.HTTP_429_TOO_MANY_REQUESTS,
}


class AnalysisService:
    """guard status -> call provider -> validate -> persist atomically.

    The meeting row is the state machine: not_started | processing | completed | failed.
    Nothing is saved unless validation passes; on any failure the previous analysis and action items stay as they were.
    """

    @staticmethod
    def analyze(meeting_id: int, owner_id: int) -> Meeting:
        meeting = Meeting.get(meeting_id=meeting_id, owner_id=owner_id)
        AnalysisService.check_transcript_length(meeting)
        AnalysisService.start(meeting_id, owner_id)
        try:
            request = AnalysisService.build_request(meeting)
            provider = get_provider()
            raw = AnalysisService.call_provider(provider, request)
            validated, _ = AnalysisOutputValidator(request).validate(raw)
            AnalysisService.persist(meeting_id, validated, provider)
        except ProviderError as error:
            AnalysisService.fail(meeting_id, owner_id, error.code, type(error).__name__)
        except InvalidAnalysisOutput as error:
            logger.warning("Analysis output rejected for meeting %s: %s", meeting_id, error.reasons)
            AnalysisService.fail(meeting_id, owner_id, Constants.ai_error_invalid, "InvalidAnalysisOutput")
        except Exception as error:  # a bug or database failure: still leave the meeting in a clean, retryable state
            AnalysisService.fail(meeting_id, owner_id, Constants.ai_error_internal, type(error).__name__)
        return Meeting.get(meeting_id=meeting_id, owner_id=owner_id)

    @staticmethod
    def check_transcript_length(meeting: Meeting) -> None:
        if len(meeting.transcript) > Configurations.ai_max_transcript_chars:
            raise ValidationErrors([{"field": "meeting_id", "message": Constants.analysis_transcript_too_long}])

    @staticmethod
    def start(meeting_id: int, owner_id: int) -> None:
        """Atomic compare-and-set to `processing`. A run that died mid-way stops blocking after the stale window."""
        now = timezone.now()
        stale_before = now - timedelta(seconds=Configurations.ai_timeout_seconds + Constants.ai_stale_grace_seconds)
        claimed = (
            Meeting.objects.owned_by(owner_id)
            .filter(meeting_id=meeting_id)
            .filter(~Q(analysis_status=AnalysisStatus.PROCESSING) | Q(updated_at__lt=stale_before))
            .update(analysis_status=AnalysisStatus.PROCESSING, updated_at=now)
        )
        if not claimed:
            raise ConflictErrors([Constants.analysis_running])

    @staticmethod
    def build_request(meeting: Meeting) -> AnalysisRequest:
        return AnalysisRequest(
            transcript=meeting.transcript,
            meeting_date=meeting.meeting_date,
            meeting_type=meeting.meeting_type,
            participants=tuple(meeting.participants),
        )

    @staticmethod
    def call_provider(provider: MeetingAnalysisProvider, request: AnalysisRequest) -> dict:
        """The one narrow try around an external call: any provider failure becomes a coded ProviderError."""
        try:
            return provider.analyze(request)
        except ProviderError:
            raise
        except Exception as error:
            logger.error("Provider %s raised %s", provider.name, type(error).__name__)
            logger.debug("Provider failure detail", exc_info=True)
            raise ProviderError() from None

    @staticmethod
    def persist(meeting_id: int, validated: dict, provider: MeetingAnalysisProvider) -> None:
        now = timezone.now()
        with transaction.atomic():
            MeetingAnalysis.objects.update_or_create(
                meeting_id=meeting_id,
                defaults={
                    "summary": validated["summary"],
                    "discussion_points": validated["discussion_points"],
                    "decisions": validated["decisions"],
                    "risks": validated["risks"],
                    "unanswered_questions": validated["unanswered_questions"],
                    "provider_name": provider.name,
                    "provider_model": provider.model,
                },
            )
            ActionItem.objects.filter(meeting_id=meeting_id, source=Source.AI, is_edited=False).delete()
            ActionItem.objects.bulk_create([AnalysisService.to_action_item(meeting_id, item) for item in validated["action_items"]])
            Meeting.objects.filter(meeting_id=meeting_id).update(
                analysis_status=AnalysisStatus.COMPLETED,
                analysis_error_code=None,
                analyzed_at=now,
                transcript_changed_since_analysis=False,
                updated_at=now,
            )

    @staticmethod
    def to_action_item(meeting_id: int, item: dict) -> ActionItem:
        return ActionItem(
            meeting_id=meeting_id,
            description=item["description"],
            owner_name=item["owner"] or "",
            due_date=item["due_date"],
            due_date_text=item["due_date_text"] or "",
            priority=item["priority"] or Priority.MEDIUM,
            source=Source.AI,
            evidence_quote=item["evidence"],
        )

    @staticmethod
    def fail(meeting_id: int, owner_id: int, code: str, reason: str) -> None:
        """Record the failure, then tell the client generically. Prior analysis and action items are untouched."""
        logger.error("Analysis failed for meeting %s: %s (%s)", meeting_id, code, reason)
        Meeting.objects.owned_by(owner_id).filter(meeting_id=meeting_id).update(
            analysis_status=AnalysisStatus.FAILED, analysis_error_code=code, updated_at=timezone.now()
        )
        http_status = FAILURE_HTTP_STATUS.get(code, status.HTTP_502_BAD_GATEWAY)
        raise UpstreamErrors(http_status, Constants.ai_failed, [{"code": code, "message": Constants.ai_failed}])
