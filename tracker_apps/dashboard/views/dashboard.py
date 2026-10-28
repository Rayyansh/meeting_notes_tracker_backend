from rest_framework import status
from rest_framework.response import Response

from tracker.constants import Constants
from tracker_apps.common.common import Common
from tracker_apps.common.utils import Utils
from tracker_apps.dashboard.dataclasses.request.get.dashboard import DashboardGet
from tracker_apps.dashboard.serializers.response.get.dashboard import DashboardResponseSerializer
from tracker_apps.dashboard.utils import DashboardUtils


class DashboardView:
    def __init__(self) -> None:
        self.data_get = Constants.dashboard_success

    @Common(response_handler=DashboardResponseSerializer).exception_handler
    def summary_extract(self, params: DashboardGet) -> Response:
        return Response(
            status=status.HTTP_200_OK,
            data=Utils.success_response_data(message=self.data_get, data=DashboardUtils.summary(owner_id=params.user_id)),
        )
