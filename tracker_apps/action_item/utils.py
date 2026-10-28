from tracker_apps.action_item.models.action_item import ActionItem
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
    def response(item: ActionItem) -> dict:
        """Missing values are stored blank/NULL and always returned as null, never as placeholders."""
        row = {column: getattr(item, column) for column in ACTION_ITEM_COLUMNS}
        for column in BLANK_AS_NULL:
            row[column] = row[column] or None
        return Utils.map_columns(row, ACTION_ITEM_COLUMNS)
