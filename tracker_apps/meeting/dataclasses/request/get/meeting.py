from dataclasses import dataclass

from tracker_apps.common.dataclasses.get_all import GetAll


@dataclass
class MeetingGet:
    meeting_id: int


@dataclass
class MeetingGetAll(GetAll):
    meeting_type: str = ""
