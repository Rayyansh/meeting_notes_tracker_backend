from django.db import models


class Priority(models.TextChoices):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class Status(models.TextChoices):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    BLOCKED = "Blocked"
    COMPLETED = "Completed"


class Source(models.TextChoices):
    AI = "ai"
    MANUAL = "manual"
