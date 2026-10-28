from tracker_apps.common.utils import Utils
from tracker_apps.meeting.models.meeting import Meeting

MEETING_LIST_COLUMNS: dict[str, str] = {
    "meeting_id": "meetingId",
    "title": "title",
    "meeting_date": "meetingDate",
    "meeting_type": "meetingType",
    "participants": "participants",
    "analysis_status": "analysisStatus",
    "created_at": "createdAt",
    "updated_at": "updatedAt",
}

MEETING_DETAIL_COLUMNS: dict[str, str] = {
    **MEETING_LIST_COLUMNS,
    "transcript": "transcript",
    "transcript_source": "transcriptSource",
    "transcript_filename": "transcriptFilename",
    "notes": "notes",
    "analysis_error_code": "analysisErrorCode",
    "analyzed_at": "analyzedAt",
    "transcript_changed_since_analysis": "transcriptChangedSinceAnalysis",
}


class MeetingUtils:
    @staticmethod
    def detail_response(meeting: Meeting) -> dict:
        row = {column: getattr(meeting, column) for column in MEETING_DETAIL_COLUMNS}
        return Utils.map_columns(row, MEETING_DETAIL_COLUMNS)

    @staticmethod
    def list_response(meeting: Meeting, columns: list[str]) -> dict:
        wanted = {column: MEETING_LIST_COLUMNS[column] for column in (columns or MEETING_LIST_COLUMNS)}
        row = {column: getattr(meeting, column) for column in wanted}
        return Utils.map_columns(row, wanted)
