from django.db import models


class MeetingType(models.TextChoices):
    CLIENT = "Client Meeting"
    SALES = "Sales Meeting"
    PROJECT = "Project Meeting"
    INTERNAL = "Internal Meeting"
    REQUIREMENT = "Requirement Discussion"
    RETROSPECTIVE = "Retrospective"
    OTHER = "Other"


class AnalysisStatus(models.TextChoices):
    NOT_STARTED = "not_started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptSource(models.TextChoices):
    TEXT = "text"
    FILE = "file"
