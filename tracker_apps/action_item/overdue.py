from datetime import date

from django.db.models import Q

from tracker_apps.action_item.choices import Status
from tracker_apps.common.clock import Clock


class Overdue:
    """The single definition of overdue: due before today and not Completed. Never stored.

    The list filter, the `isOverdue` flag in responses and the dashboard all go through here so they cannot disagree.
    """

    @staticmethod
    def condition(today: date | None = None) -> Q:
        return Q(due_date__lt=today or Clock.today()) & ~Q(status=Status.COMPLETED)

    @staticmethod
    def is_overdue(due_date: date | None, status: str, today: date | None = None) -> bool:
        return due_date is not None and due_date < (today or Clock.today()) and status != Status.COMPLETED
