from tracker_apps.action_item.utils import ActionItemUtils
from tracker_apps.common.utils import Utils
from tracker_apps.meeting.choices import AnalysisStatus
from tracker_apps.meeting.models.meeting import Meeting
from tracker_apps.meeting.models.meeting_analysis import MeetingAnalysis

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


ANALYSIS_COLUMNS: dict[str, str] = {
    "analysis_id": "analysisId",
    "summary": "summary",
    "discussion_points": "discussionPoints",
    "decisions": "decisions",
    "risks": "risks",
    "unanswered_questions": "unansweredQuestions",
    "provider_name": "providerName",
    "provider_model": "providerModel",
    "created_at": "createdAt",
    "updated_at": "updatedAt",
}


class MeetingUtils:
    @staticmethod
    def detail_response(meeting: Meeting) -> dict:
        row = {column: getattr(meeting, column) for column in MEETING_DETAIL_COLUMNS}
        detail = Utils.map_columns(row, MEETING_DETAIL_COLUMNS)
        detail["analysis"] = MeetingUtils.analysis_payload(meeting)
        detail["actionItems"] = MeetingUtils.action_items_payload(meeting)
        return detail

    @staticmethod
    def analysis_payload(meeting: Meeting) -> dict | None:
        """A reset (`not_started`) hides the old analysis; the row is replaced on the next run."""
        analysis: MeetingAnalysis | None = getattr(meeting, "analysis", None)
        if analysis is None or meeting.analysis_status == AnalysisStatus.NOT_STARTED:
            return None
        return Utils.map_columns({column: getattr(analysis, column) for column in ANALYSIS_COLUMNS}, ANALYSIS_COLUMNS)

    @staticmethod
    def action_items_payload(meeting: Meeting) -> list[dict]:
        return [ActionItemUtils.response(item) for item in meeting.action_items.soonest_due_first()]

    @staticmethod
    def analysis_state_response(meeting: Meeting) -> dict:
        return {
            "meetingId": meeting.meeting_id,
            "analysisStatus": meeting.analysis_status,
            "analysisErrorCode": meeting.analysis_error_code,
            "analyzedAt": meeting.analyzed_at,
            "transcriptChangedSinceAnalysis": meeting.transcript_changed_since_analysis,
            "analysis": MeetingUtils.analysis_payload(meeting),
            "actionItems": MeetingUtils.action_items_payload(meeting),
        }

    @staticmethod
    def list_response(meeting: Meeting, columns: list[str]) -> dict:
        wanted = {column: MEETING_LIST_COLUMNS[column] for column in (columns or MEETING_LIST_COLUMNS)}
        row = {column: getattr(meeting, column) for column in wanted}
        return Utils.map_columns(row, wanted)
