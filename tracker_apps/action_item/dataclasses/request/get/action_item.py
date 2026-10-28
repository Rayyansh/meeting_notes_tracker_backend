from dataclasses import dataclass

from tracker_apps.common.dataclasses.get_all import GetAll


@dataclass
class ActionItemGet:
    action_item_id: int


@dataclass
class ActionItemGetAll(GetAll):
    meeting_id: int | None = None
    status: str = ""
    priority: str = ""
    owner: str = ""
    is_overdue: bool | None = None
