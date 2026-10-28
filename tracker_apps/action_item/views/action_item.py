from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from tracker.constants import Constants
from tracker_apps.action_item.dataclasses.request.create.action_item import ActionItemCreate
from tracker_apps.action_item.dataclasses.request.delete.action_item import ActionItemDelete
from tracker_apps.action_item.dataclasses.request.get.action_item import ActionItemGet, ActionItemGetAll
from tracker_apps.action_item.dataclasses.request.update.action_item import ActionItemUpdate
from tracker_apps.action_item.models.action_item import ActionItem
from tracker_apps.action_item.serializers.response.get.action_item import ActionItemResponseSerializer
from tracker_apps.action_item.serializers.response.get_all.action_item import ActionItemListResponseSerializer
from tracker_apps.action_item.utils import ActionItemUtils
from tracker_apps.common.common import Common
from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer
from tracker_apps.common.utils import Utils
from tracker_apps.meeting.models.meeting import Meeting


class ActionItemView:
    def __init__(self) -> None:
        self.data_create = Constants.action_item_create_success
        self.data_update = Constants.action_item_update_success
        self.data_delete = Constants.action_item_delete_success
        self.data_get = Constants.data_get
        self.data_no_match = Constants.data_no_match

    @Common(response_handler=ActionItemResponseSerializer).exception_handler
    def create_extract(self, params: ActionItemCreate) -> Response:
        with transaction.atomic():
            meeting = Meeting.get(meeting_id=params.meeting_id, owner_id=params.user_id)  # re-verify the foreign id
            item = ActionItem.create(params=params, meeting_id=meeting.meeting_id)
        item = ActionItem.get(action_item_id=item.action_item_id, owner_id=params.user_id)
        return Response(
            status=status.HTTP_201_CREATED,
            data=Utils.success_response_data(message=self.data_create, data=ActionItemUtils.response(item)),
        )

    @Common(response_handler=ActionItemResponseSerializer).exception_handler
    def update_extract(self, params: ActionItemUpdate) -> Response:
        with transaction.atomic():
            item = ActionItem.update(params=params, owner_id=params.user_id)
        return Response(
            status=status.HTTP_200_OK,
            data=Utils.success_response_data(message=self.data_update, data=ActionItemUtils.response(item)),
        )

    @Common(response_handler=ActionItemResponseSerializer).exception_handler
    def get_extract(self, params: ActionItemGet) -> Response:
        item = ActionItem.get(action_item_id=params.action_item_id, owner_id=params.user_id)
        return Response(
            status=status.HTTP_200_OK,
            data=Utils.success_response_data(message=self.data_get, data=ActionItemUtils.response(item)),
        )

    @Common(response_handler=ActionItemListResponseSerializer).exception_handler
    def get_all_extract(self, params: ActionItemGetAll) -> Response:
        queryset = ActionItem.get_all(params=params, owner_id=params.user_id)
        rows, total_page = Utils.paginate(queryset, params.page_num, params.limit)
        items = [ActionItemUtils.response(item, params.values_list) for item in rows]
        page = Utils.add_page_parameter(items, params.page_num, total_page, params.present_url)
        message = self.data_get if items else self.data_no_match
        return Response(status=status.HTTP_200_OK, data=Utils.success_response_data(message=message, data=page))

    @Common(response_handler=ApiResponseSerializer).exception_handler
    def delete_extract(self, params: ActionItemDelete) -> Response:
        with transaction.atomic():
            ActionItem.get(action_item_id=params.action_item_id, owner_id=params.user_id).remove()
        return Response(status=status.HTTP_200_OK, data=Utils.success_response_data(message=self.data_delete))
