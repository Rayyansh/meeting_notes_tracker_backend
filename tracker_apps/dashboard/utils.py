from django.db.models import Count, Q

from tracker.constants import Constants

from tracker_apps.action_item.choices import Priority, Status
from tracker_apps.action_item.models.action_item import ActionItem
from tracker_apps.action_item.overdue import Overdue
from tracker_apps.action_item.utils import ActionItemUtils
from tracker_apps.meeting.models.meeting import Meeting
from tracker_apps.meeting.utils import MeetingUtils


class DashboardUtils:
    @staticmethod
    def action_item_counts(owner_id: int) -> dict:
        """All counters in one query over the caller's items. Overdue uses the same rule as the list filter."""
        return ActionItem.objects.owned_by(owner_id).aggregate(
            total=Count("action_item_id"),
            open=Count("action_item_id", filter=Q(status=Status.OPEN)),
            in_progress=Count("action_item_id", filter=Q(status=Status.IN_PROGRESS)),
            blocked=Count("action_item_id", filter=Q(status=Status.BLOCKED)),
            completed=Count("action_item_id", filter=Q(status=Status.COMPLETED)),
            overdue=Count("action_item_id", filter=Overdue.condition()),
            low=Count("action_item_id", filter=Q(priority=Priority.LOW)),
            medium=Count("action_item_id", filter=Q(priority=Priority.MEDIUM)),
            high=Count("action_item_id", filter=Q(priority=Priority.HIGH)),
        )

    @staticmethod
    def summary(owner_id: int) -> dict:
        counts = DashboardUtils.action_item_counts(owner_id)
        recent = Meeting.objects.owned_by(owner_id).order_by("-created_at", "-meeting_id")[: Constants.dashboard_recent_limit]
        upcoming = (
            ActionItem.objects.owned_by(owner_id)
            .with_meeting()
            .exclude(status=Status.COMPLETED)
            .filter(due_date__isnull=False)
            .order_by("due_date", "action_item_id")[: Constants.dashboard_upcoming_limit]
        )
        return {
            "totalMeetings": Meeting.objects.owned_by(owner_id).count(),
            "totalActionItems": counts["total"],
            "openActionItems": counts["open"],
            "inProgressActionItems": counts["in_progress"],
            "blockedActionItems": counts["blocked"],
            "completedActionItems": counts["completed"],
            "unfinishedActionItems": counts["total"] - counts["completed"],
            "overdueActionItems": counts["overdue"],
            "actionItemsByPriority": {Priority.LOW: counts["low"], Priority.MEDIUM: counts["medium"], Priority.HIGH: counts["high"]},
            "recentMeetings": [MeetingUtils.list_response(meeting, []) for meeting in recent],
            "upcomingActionItems": [ActionItemUtils.response(item) for item in upcoming],
        }
