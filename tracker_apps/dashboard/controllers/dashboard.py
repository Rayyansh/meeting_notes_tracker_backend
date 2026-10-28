from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from tracker_apps.common.serializer_validations import SerializerValidations
from tracker_apps.dashboard.serializers.request.get.dashboard import DashboardGetSerializer
from tracker_apps.dashboard.serializers.response.get.dashboard import DashboardResponseSerializer
from tracker_apps.dashboard.views.dashboard import DashboardView


class DashboardViewController:
    @staticmethod
    @extend_schema(responses={200: DashboardResponseSerializer}, tags=["dashboard"])
    @api_view(["GET"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=DashboardGetSerializer).validate
    def summary(request: Request) -> Response:
        return DashboardView().summary_extract(params=request.params)
