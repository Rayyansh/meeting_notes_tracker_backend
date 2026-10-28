from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from tracker_apps.common.serializer_validations import SerializerValidations
from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer
from tracker_apps.common.swagger import SwaggerPage
from tracker_apps.meeting.choices import MeetingType
from tracker_apps.meeting.serializers.request.create.meeting import MeetingCreateSerializer
from tracker_apps.meeting.serializers.request.delete.meeting import MeetingDeleteSerializer
from tracker_apps.meeting.serializers.request.get.meeting import MeetingGetAllSerializer, MeetingGetSerializer
from tracker_apps.meeting.serializers.request.update.meeting import MeetingUpdateSerializer
from tracker_apps.meeting.serializers.response.get.meeting import MeetingResponseSerializer
from tracker_apps.meeting.serializers.response.get_all.meeting import MeetingListResponseSerializer
from tracker_apps.meeting.views.meeting import MeetingView

TAG = ["meeting"]


class MeetingViewController:
    @staticmethod
    @extend_schema(request={"application/json": MeetingCreateSerializer, "multipart/form-data": MeetingCreateSerializer}, responses={201: MeetingResponseSerializer}, tags=TAG)
    @api_view(["POST"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=MeetingCreateSerializer).validate
    def create(request: Request) -> Response:
        return MeetingView().create_extract(params=request.params)

    @staticmethod
    @extend_schema(request={"application/json": MeetingUpdateSerializer, "multipart/form-data": MeetingUpdateSerializer}, responses={200: MeetingResponseSerializer}, tags=TAG)
    @api_view(["PUT"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=MeetingUpdateSerializer).validate
    def update(request: Request) -> Response:
        return MeetingView().update_extract(params=request.params)

    @staticmethod
    @extend_schema(parameters=[MeetingGetSerializer], responses={200: MeetingResponseSerializer}, tags=TAG)
    @api_view(["GET"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=MeetingGetSerializer).validate
    def get(request: Request) -> Response:
        return MeetingView().get_extract(params=request.params)

    @staticmethod
    @extend_schema(
        parameters=SwaggerPage.get_all_parameters(
            sort_fields=MeetingGetAllSerializer.allowed_sort_fields,
            default_sort_by=MeetingGetAllSerializer.default_sort_by,
            default_sort_order=MeetingGetAllSerializer.default_sort_order,
        )
        + [OpenApiParameter("meeting_type", OpenApiTypes.STR, OpenApiParameter.QUERY, False, "Filter by meeting type", enum=MeetingType.values)],
        responses={200: MeetingListResponseSerializer},
        tags=TAG,
    )
    @api_view(["GET"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=MeetingGetAllSerializer).validate
    def get_all(request: Request) -> Response:
        return MeetingView().get_all_extract(params=request.params)

    @staticmethod
    @extend_schema(parameters=[MeetingDeleteSerializer], responses={200: ApiResponseSerializer}, tags=TAG)
    @api_view(["DELETE"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=MeetingDeleteSerializer).validate
    def delete(request: Request) -> Response:
        return MeetingView().delete_extract(params=request.params)
