from django.db import models

from tracker_apps.common.fields import UnicodeJSONEncoder


class MeetingAnalysis(models.Model):
    """The latest analysis of a meeting; a re-run replaces it."""

    analysis_id = models.AutoField(primary_key=True)
    meeting = models.OneToOneField("meeting.Meeting", on_delete=models.CASCADE, related_name="analysis")
    summary = models.TextField()
    discussion_points = models.JSONField(default=list, encoder=UnicodeJSONEncoder)
    decisions = models.JSONField(default=list, encoder=UnicodeJSONEncoder)
    risks = models.JSONField(default=list, encoder=UnicodeJSONEncoder)
    unanswered_questions = models.JSONField(default=list, encoder=UnicodeJSONEncoder)
    provider_name = models.CharField(max_length=50)
    provider_model = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "meeting_analyses"

    def __str__(self) -> str:
        return f"Analysis of meeting {self.meeting_id}"
