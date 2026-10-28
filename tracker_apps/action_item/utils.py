from tracker_apps.action_item.models.action_item import ActionItem
from tracker_apps.action_item.overdue import Overdue
from tracker_apps.common.utils import Utils

ACTION_ITEM_COLUMNS: dict[str, str] = {
    "action_item_id": "actionItemId",
    "meeting_id": "meetingId",
    "description": "description",
    "owner_name": "ownerName",
    "due_date": "dueDate",
    "due_date_text": "dueDateText",
    "priority": "priority",
    "status": "status",
    "source": "source",
    "evidence_quote": "evidenceQuote",
    "is_edited": "isEdited",
    "completed_at": "completedAt",
    "created_at": "createdAt",
    "updated_at": "updatedAt",
}
BLANK_AS_NULL: tuple[str, ...] = ("owner_name", "due_date_text", "evidence_quote")


class ActionItemUtils:
    @staticmethod
    def response(item: ActionItem, columns: list[str] | None = None) -> dict:
        """Missing values are stored blank/NULL and always returned as null, never as placeholders.
        `columns` limits the db columns returned (the `values` query parameter); derived fields are then omitted."""
        wanted = {column: ACTION_ITEM_COLUMNS[column] for column in (columns or ACTION_ITEM_COLUMNS)}
        row = {column: getattr(item, column) for column in wanted}
        for column in BLANK_AS_NULL:
            if column in row:
                row[column] = row[column] or None
        data = Utils.map_columns(row, wanted)
        if not columns:
            data["meetingTitle"] = item.meeting.title
            data["isOverdue"] = Overdue.is_overdue(item.due_date, item.status)
        return data
