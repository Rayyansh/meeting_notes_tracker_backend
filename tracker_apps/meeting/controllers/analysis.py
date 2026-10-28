from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from tracker_apps.common.serializer_validations import SerializerValidations
from tracker_apps.meeting.serializers.request.create.analysis import AnalysisCreateSerializer
from tracker_apps.meeting.serializers.request.get.analysis import AnalysisGetSerializer
from tracker_apps.meeting.serializers.request.update.analysis import AnalysisUpdateSerializer
from tracker_apps.meeting.serializers.response.get.analysis import AnalysisResponseSerializer
from tracker_apps.meeting.views.analysis import AnalysisView

TAG = ["analysis"]


class AnalysisViewController:
    @staticmethod
    @extend_schema(request=AnalysisCreateSerializer, responses={200: AnalysisResponseSerializer}, tags=TAG)
    @api_view(["POST"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=AnalysisCreateSerializer).validate
    def create(request: Request) -> Response:
        return AnalysisView().create_extract(params=request.params)

    @staticmethod
    @extend_schema(parameters=[AnalysisGetSerializer], responses={200: AnalysisResponseSerializer}, tags=TAG)
    @api_view(["GET"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=AnalysisGetSerializer).validate
    def get(request: Request) -> Response:
        return AnalysisView().get_extract(params=request.params)

    @staticmethod
    @extend_schema(request=AnalysisUpdateSerializer, responses={200: AnalysisResponseSerializer}, tags=TAG)
    @api_view(["PUT"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=AnalysisUpdateSerializer).validate
    def update(request: Request) -> Response:
        return AnalysisView().update_extract(params=request.params)
