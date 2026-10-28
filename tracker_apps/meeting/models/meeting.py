from django.conf import settings
from django.db import models
from django.db.models import Q, QuerySet

from tracker_apps.common.exceptions.http_errors import NotFoundErrors
from tracker_apps.common.fields import UnicodeJSONEncoder
from tracker_apps.meeting.choices import AnalysisStatus, MeetingType, TranscriptSource
from tracker_apps.meeting.dataclasses.request.create.meeting import MeetingCreate
from tracker_apps.meeting.dataclasses.request.get.meeting import MeetingGetAll

UPDATABLE_FIELDS: tuple[str, ...] = ("title", "meeting_date", "meeting_type", "participants", "notes")


class MeetingQuerySet(models.QuerySet):
    def owned_by(self, user: object) -> "MeetingQuerySet":
        """The only entry point for reading meetings: scoped to the owner (a user or a user id)."""
        return self.filter(owner_id=getattr(user, "pk", user))


class Meeting(models.Model):
    meeting_id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meetings")
    title = models.CharField(max_length=200)
    meeting_date = models.DateField()
    meeting_type = models.CharField(max_length=30, choices=MeetingType.choices)
    participants = models.JSONField(default=list, encoder=UnicodeJSONEncoder)
    transcript = models.TextField()
    transcript_source = models.CharField(max_length=10, choices=TranscriptSource.choices, default=TranscriptSource.TEXT)
    transcript_filename = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    analysis_status = models.CharField(max_length=20, choices=AnalysisStatus.choices, default=AnalysisStatus.NOT_STARTED)
    analysis_error_code = models.CharField(max_length=50, null=True, blank=True)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    transcript_changed_since_analysis = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MeetingQuerySet.as_manager()

    class Meta:
        db_table = "meetings"
        indexes = [
            models.Index(fields=["owner", "-created_at"], name="meeting_owner_created_idx"),
            models.Index(fields=["owner", "meeting_date"], name="meeting_owner_date_idx"),
        ]

    def __str__(self) -> str:
        return self.title

    @staticmethod
    def create(params: MeetingCreate, owner_id: int) -> "Meeting":
        return Meeting.objects.create(
            owner_id=owner_id,
            title=params.title,
            meeting_date=params.meeting_date,
            meeting_type=params.meeting_type,
            participants=params.participants,
            transcript=params.transcript,
            notes=params.notes,
        )

    @staticmethod
    def get(meeting_id: int, owner_id: int) -> "Meeting":
        meeting = Meeting.objects.owned_by(owner_id).filter(meeting_id=meeting_id).first()
        if meeting is None:
            raise NotFoundErrors()
        return meeting

    @staticmethod
    def get_all(params: MeetingGetAll, owner_id: int) -> QuerySet:
        queryset = Meeting.objects.owned_by(owner_id)
        if params.search_key:
            queryset = queryset.filter(
                Q(title__icontains=params.search_key)
                | Q(participants__icontains=params.search_key)
                | Q(notes__icontains=params.search_key)
            )
        if params.meeting_type:
            queryset = queryset.filter(meeting_type=params.meeting_type)
        if params.from_date:
            queryset = queryset.filter(meeting_date__gte=params.from_date)
        if params.to_date:
            queryset = queryset.filter(meeting_date__lte=params.to_date)
        return queryset.order_by(params.ordering, "-meeting_id")

    def remove(self) -> None:
        self.delete()
