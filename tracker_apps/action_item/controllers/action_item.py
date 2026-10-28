from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from tracker_apps.action_item.choices import Priority, Status
from tracker_apps.action_item.serializers.request.create.action_item import ActionItemCreateSerializer
from tracker_apps.action_item.serializers.request.delete.action_item import ActionItemDeleteSerializer
from tracker_apps.action_item.serializers.request.get.action_item import ActionItemGetAllSerializer, ActionItemGetSerializer
from tracker_apps.action_item.serializers.request.update.action_item import ActionItemUpdateSerializer
from tracker_apps.action_item.serializers.response.get.action_item import ActionItemResponseSerializer
from tracker_apps.action_item.serializers.response.get_all.action_item import ActionItemListResponseSerializer
from tracker_apps.action_item.views.action_item import ActionItemView
from tracker_apps.common.serializer_validations import SerializerValidations
from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer
from tracker_apps.common.swagger import SwaggerPage

TAG = ["action_item"]
QUERY = OpenApiParameter.QUERY
FILTERS = [
    OpenApiParameter("meeting_id", OpenApiTypes.INT, QUERY, False, "Only items of this meeting"),
    OpenApiParameter("status", OpenApiTypes.STR, QUERY, False, "Filter by status", enum=Status.values),
    OpenApiParameter("priority", OpenApiTypes.STR, QUERY, False, "Filter by priority", enum=Priority.values),
    OpenApiParameter("owner", OpenApiTypes.STR, QUERY, False, "Owner name contains (case-insensitive)"),
    OpenApiParameter("is_overdue", OpenApiTypes.BOOL, QUERY, False, "true: overdue only; false: not overdue"),
]


class ActionItemViewController:
    @staticmethod
    @extend_schema(request=ActionItemCreateSerializer, responses={201: ActionItemResponseSerializer}, tags=TAG)
    @api_view(["POST"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=ActionItemCreateSerializer).validate
    def create(request: Request) -> Response:
        return ActionItemView().create_extract(params=request.params)

    @staticmethod
    @extend_schema(request=ActionItemUpdateSerializer, responses={200: ActionItemResponseSerializer}, tags=TAG)
    @api_view(["PUT"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=ActionItemUpdateSerializer).validate
    def update(request: Request) -> Response:
        return ActionItemView().update_extract(params=request.params)

    @staticmethod
    @extend_schema(parameters=[ActionItemGetSerializer], responses={200: ActionItemResponseSerializer}, tags=TAG)
    @api_view(["GET"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=ActionItemGetSerializer).validate
    def get(request: Request) -> Response:
        return ActionItemView().get_extract(params=request.params)

    @staticmethod
    @extend_schema(
        parameters=SwaggerPage.get_all_parameters(
            sort_fields=ActionItemGetAllSerializer.allowed_sort_fields,
            default_sort_by=ActionItemGetAllSerializer.default_sort_by,
            default_sort_order=ActionItemGetAllSerializer.default_sort_order,
        )
        + FILTERS,
        responses={200: ActionItemListResponseSerializer},
        tags=TAG,
    )
    @api_view(["GET"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=ActionItemGetAllSerializer).validate
    def get_all(request: Request) -> Response:
        return ActionItemView().get_all_extract(params=request.params)

    @staticmethod
    @extend_schema(parameters=[ActionItemDeleteSerializer], responses={200: ApiResponseSerializer}, tags=TAG)
    @api_view(["DELETE"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=ActionItemDeleteSerializer).validate
    def delete(request: Request) -> Response:
        return ActionItemView().delete_extract(params=request.params)
