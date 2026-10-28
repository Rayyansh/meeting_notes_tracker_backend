from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from tracker.constants import Constants
from tracker_apps.common.common import Common
from tracker_apps.common.exceptions.http_errors import ConflictErrors
from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer
from tracker_apps.common.utils import Utils
from tracker_apps.meeting.choices import AnalysisStatus
from tracker_apps.meeting.dataclasses.request.create.meeting import MeetingCreate
from tracker_apps.meeting.dataclasses.request.delete.meeting import MeetingDelete
from tracker_apps.meeting.dataclasses.request.get.meeting import MeetingGet, MeetingGetAll
from tracker_apps.meeting.dataclasses.request.update.meeting import MeetingUpdate
from tracker_apps.meeting.models.meeting import UPDATABLE_FIELDS, Meeting
from tracker_apps.meeting.serializers.response.get.meeting import MeetingResponseSerializer
from tracker_apps.meeting.serializers.response.get_all.meeting import MeetingListResponseSerializer
from tracker_apps.meeting.utils import MeetingUtils


class MeetingView:
    def __init__(self) -> None:
        self.data_create = Constants.meeting_create_success
        self.data_update = Constants.meeting_update_success
        self.data_delete = Constants.meeting_delete_success
        self.data_get = Constants.data_get
        self.data_no_match = Constants.data_no_match

    @Common(response_handler=MeetingResponseSerializer).exception_handler
    def create_extract(self, params: MeetingCreate) -> Response:
        with transaction.atomic():
            meeting = Meeting.create(params=params, owner_id=params.user_id)
        return Response(
            status=status.HTTP_201_CREATED,
            data=Utils.success_response_data(message=self.data_create, data=MeetingUtils.detail_response(meeting)),
        )

    @Common(response_handler=MeetingResponseSerializer).exception_handler
    def update_extract(self, params: MeetingUpdate) -> Response:
        with transaction.atomic():
            meeting = Meeting.get(meeting_id=params.meeting_id, owner_id=params.user_id)
            self.apply_update(meeting, params)
        return Response(
            status=status.HTTP_200_OK,
            data=Utils.success_response_data(message=self.data_update, data=MeetingUtils.detail_response(meeting)),
        )

    @Common(response_handler=MeetingResponseSerializer).exception_handler
    def get_extract(self, params: MeetingGet) -> Response:
        meeting = Meeting.get(meeting_id=params.meeting_id, owner_id=params.user_id)
        return Response(
            status=status.HTTP_200_OK,
            data=Utils.success_response_data(message=self.data_get, data=MeetingUtils.detail_response(meeting)),
        )

    @Common(response_handler=MeetingListResponseSerializer).exception_handler
    def get_all_extract(self, params: MeetingGetAll) -> Response:
        rows, total_page = Utils.paginate(Meeting.get_all(params=params, owner_id=params.user_id), params.page_num, params.limit)
        items = [MeetingUtils.list_response(meeting, params.values_list) for meeting in rows]
        page = Utils.add_page_parameter(items, params.page_num, total_page, params.present_url)
        message = self.data_get if items else self.data_no_match
        return Response(status=status.HTTP_200_OK, data=Utils.success_response_data(message=message, data=page))

    @Common(response_handler=ApiResponseSerializer).exception_handler
    def delete_extract(self, params: MeetingDelete) -> Response:
        with transaction.atomic():
            Meeting.get(meeting_id=params.meeting_id, owner_id=params.user_id).remove()
        return Response(status=status.HTTP_200_OK, data=Utils.success_response_data(message=self.data_delete))

    @staticmethod
    def apply_update(meeting: Meeting, params: MeetingUpdate) -> None:
        changed = [name for name in UPDATABLE_FIELDS if getattr(params, name) is not None]
        for name in changed:
            setattr(meeting, name, getattr(params, name))
        if params.transcript is not None and params.transcript != meeting.transcript:
            MeetingView.apply_transcript_change(meeting, params)
            changed += ["transcript", "analysis_status", "analysis_error_code", "analyzed_at", "transcript_changed_since_analysis"]
        meeting.save(update_fields=list(dict.fromkeys(changed)) + ["updated_at"])

    @staticmethod
    def apply_transcript_change(meeting: Meeting, params: MeetingUpdate) -> None:
        if meeting.analysis_status == AnalysisStatus.PROCESSING:
            raise ConflictErrors([Constants.meeting_analysis_running])
        meeting.transcript = params.transcript
        if meeting.analysis_status == AnalysisStatus.NOT_STARTED:
            return
        if params.reset_analysis:
            meeting.analysis_status = AnalysisStatus.NOT_STARTED
            meeting.analysis_error_code = None
            meeting.analyzed_at = None
            meeting.transcript_changed_since_analysis = False
        else:
            meeting.transcript_changed_since_analysis = True
