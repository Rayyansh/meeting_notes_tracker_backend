from django.db import models
from django.db.models import Case, F, IntegerField, Q, QuerySet, Value, When

from tracker_apps.action_item.choices import Priority, Source, Status
from tracker_apps.action_item.dataclasses.request.create.action_item import ActionItemCreate
from tracker_apps.action_item.dataclasses.request.get.action_item import ActionItemGetAll
from tracker_apps.action_item.dataclasses.request.update.action_item import ActionItemUpdate
from tracker_apps.action_item.overdue import Overdue
from tracker_apps.common.clock import Clock
from tracker_apps.common.exceptions.http_errors import NotFoundErrors

EDITABLE_FIELDS: tuple[str, ...] = ("description", "owner_name", "due_date", "due_date_text", "priority", "status")
PRIORITY_ORDER = [Priority.LOW, Priority.MEDIUM, Priority.HIGH]
STATUS_ORDER = [Status.OPEN, Status.IN_PROGRESS, Status.BLOCKED, Status.COMPLETED]
RANKED_SORTS: dict[str, str] = {"priority": "priority_rank", "status": "status_rank"}


def rank(field: str, order: list[str]) -> Case:
    return Case(*[When(**{field: value}, then=Value(position)) for position, value in enumerate(order)], output_field=IntegerField())


class ActionItemQuerySet(models.QuerySet):
    def owned_by(self, user: object) -> "ActionItemQuerySet":
        """Action items have no owner of their own: access flows through meeting.owner."""
        return self.filter(meeting__owner_id=getattr(user, "pk", user))

    def with_meeting(self) -> "ActionItemQuerySet":
        return self.select_related("meeting")

    def overdue(self) -> "ActionItemQuerySet":
        return self.filter(Overdue.condition())

    def not_overdue(self) -> "ActionItemQuerySet":
        return self.exclude(Overdue.condition())

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

    @staticmethod
    def create(params: ActionItemCreate, meeting_id: int) -> "ActionItem":
        """`meeting_id` must already be verified as owned by the caller (the view does this)."""
        return ActionItem.objects.create(
            meeting_id=meeting_id,
            description=params.description,
            owner_name=params.owner_name,
            due_date=params.due_date,
            due_date_text=params.due_date_text,
            priority=params.priority,
            status=params.status,
            source=Source.MANUAL,
            completed_at=Clock.now() if params.status == Status.COMPLETED else None,
        )

    @staticmethod
    def get(action_item_id: int, owner_id: int) -> "ActionItem":
        item = ActionItem.objects.owned_by(owner_id).with_meeting().filter(action_item_id=action_item_id).first()
        if item is None:
            raise NotFoundErrors()
        return item

    @staticmethod
    def get_all(params: ActionItemGetAll, owner_id: int) -> QuerySet:
        queryset = ActionItem.objects.owned_by(owner_id).with_meeting()
        if params.meeting_id:
            queryset = queryset.filter(meeting_id=params.meeting_id)
        if params.status:
            queryset = queryset.filter(status=params.status)
        if params.priority:
            queryset = queryset.filter(priority=params.priority)
        if params.owner:
            queryset = queryset.filter(owner_name__icontains=params.owner)
        if params.is_overdue is not None:
            queryset = queryset.overdue() if params.is_overdue else queryset.not_overdue()
        if params.from_date:
            queryset = queryset.filter(due_date__gte=params.from_date)
        if params.to_date:
            queryset = queryset.filter(due_date__lte=params.to_date)
        if params.search_key:
            queryset = queryset.filter(Q(description__icontains=params.search_key) | Q(owner_name__icontains=params.search_key))
        return ActionItem.ordered(queryset, params.sort_by, params.sort_order)

    @staticmethod
    def ordered(queryset: QuerySet, sort_by: str, sort_order: str) -> QuerySet:
        """Whitelisted sort. Undated items are always last; priority and status sort by meaning, not alphabetically."""
        descending = sort_order == "desc"
        queryset = queryset.annotate(priority_rank=rank("priority", PRIORITY_ORDER), status_rank=rank("status", STATUS_ORDER))
        if sort_by == "due_date":
            primary = F("due_date").desc(nulls_last=True) if descending else F("due_date").asc(nulls_last=True)
        else:
            column = RANKED_SORTS.get(sort_by, sort_by)
            primary = F(column).desc() if descending else F(column).asc()
        return queryset.order_by(primary, "action_item_id")

    @staticmethod
    def update(params: ActionItemUpdate, owner_id: int) -> "ActionItem":
        """Apply only the provided fields. Any real change marks the item edited, so a re-run of the AI analysis
        keeps it. Moving to/from Completed sets/clears completed_at."""
        item = ActionItem.get(action_item_id=params.action_item_id, owner_id=owner_id)
        changed = [name for name in EDITABLE_FIELDS if name in params.provided and getattr(params, name) != getattr(item, name)]
        for name in changed:
            setattr(item, name, getattr(params, name))
        if "due_date" in changed and "due_date_text" not in params.provided and item.due_date_text:
            item.due_date_text = ""  # the old wording no longer describes the new date
            changed.append("due_date_text")
        if "status" in changed:
            item.completed_at = Clock.now() if item.status == Status.COMPLETED else None
            changed.append("completed_at")
        if changed:
            item.is_edited = True
            changed.append("is_edited")
        item.save(update_fields=list(dict.fromkeys(changed)) + ["updated_at"])
        return item

    def remove(self) -> None:
        self.delete()
