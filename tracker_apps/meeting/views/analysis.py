from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from tracker.constants import Constants
from tracker_apps.ai_service.service import AnalysisService
from tracker_apps.common.common import Common
from tracker_apps.common.exceptions.http_errors import ConflictErrors, NotFoundErrors
from tracker_apps.common.utils import Utils
from tracker_apps.meeting.choices import AnalysisStatus
from tracker_apps.meeting.dataclasses.request.create.analysis import AnalysisCreate
from tracker_apps.meeting.dataclasses.request.get.analysis import AnalysisGet
from tracker_apps.meeting.dataclasses.request.update.analysis import AnalysisUpdate
from tracker_apps.meeting.models.meeting import Meeting
from tracker_apps.meeting.serializers.response.get.analysis import AnalysisResponseSerializer
from tracker_apps.meeting.utils import MeetingUtils


class AnalysisView:
    def __init__(self) -> None:
        self.data_create = Constants.analysis_success
        self.data_update = Constants.analysis_update_success
        self.data_get = Constants.data_get

    @Common(response_handler=AnalysisResponseSerializer).exception_handler
    def create_extract(self, params: AnalysisCreate) -> Response:
        # Deliberately not wrapped in one transaction: `processing` and `failed` must be visible and survive errors.
        meeting = AnalysisService.analyze(meeting_id=params.meeting_id, owner_id=params.user_id)
        return Response(
            status=status.HTTP_200_OK,
            data=Utils.success_response_data(message=self.data_create, data=MeetingUtils.analysis_state_response(meeting)),
        )

    @Common(response_handler=AnalysisResponseSerializer).exception_handler
    def get_extract(self, params: AnalysisGet) -> Response:
        meeting = Meeting.get(meeting_id=params.meeting_id, owner_id=params.user_id)
        return Response(
            status=status.HTTP_200_OK,
            data=Utils.success_response_data(message=self.data_get, data=MeetingUtils.analysis_state_response(meeting)),
        )

    @Common(response_handler=AnalysisResponseSerializer).exception_handler
    def update_extract(self, params: AnalysisUpdate) -> Response:
        with transaction.atomic():
            meeting = Meeting.get(meeting_id=params.meeting_id, owner_id=params.user_id)
            if meeting.analysis_status == AnalysisStatus.PROCESSING:
                raise ConflictErrors([Constants.analysis_running])
            if MeetingUtils.analysis_payload(meeting) is None:
                raise NotFoundErrors()
            meeting.analysis.summary = params.summary
            meeting.analysis.save(update_fields=["summary", "updated_at"])
        return Response(
            status=status.HTTP_200_OK,
            data=Utils.success_response_data(message=self.data_update, data=MeetingUtils.analysis_state_response(meeting)),
        )
