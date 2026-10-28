from django.db import models
from django.db.models import F

from tracker_apps.action_item.choices import Priority, Source, Status


class ActionItemQuerySet(models.QuerySet):
    def owned_by(self, user: object) -> "ActionItemQuerySet":
        """Action items have no owner of their own: access flows through meeting.owner."""
        return self.filter(meeting__owner_id=getattr(user, "pk", user))

    def soonest_due_first(self) -> "ActionItemQuerySet":
        return self.order_by(F("due_date").asc(nulls_last=True), "action_item_id")


class ActionItem(models.Model):
    action_item_id = models.AutoField(primary_key=True)
    meeting = models.ForeignKey("meeting.Meeting", on_delete=models.CASCADE, related_name="action_items")
    description = models.CharField(max_length=500)
    owner_name = models.CharField(max_length=200, blank=True, default="")
    due_date = models.DateField(null=True, blank=True)
    due_date_text = models.CharField(max_length=100, blank=True, default="")
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)
    evidence_quote = models.TextField(blank=True, default="")
    is_edited = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActionItemQuerySet.as_manager()

    class Meta:
        db_table = "action_items"
        indexes = [
            models.Index(fields=["meeting", "status"], name="action_meeting_status_idx"),
            models.Index(fields=["due_date"], name="action_due_date_idx"),
        ]

    def __str__(self) -> str:
        return self.description
