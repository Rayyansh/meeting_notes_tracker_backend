from rest_framework import serializers

from tracker_apps.action_item.choices import Priority, Status
from tracker_apps.action_item.dataclasses.request.get.action_item import ActionItemGet, ActionItemGetAll
from tracker_apps.action_item.serializers.request import fields
from tracker_apps.action_item.utils import ACTION_ITEM_COLUMNS
from tracker_apps.common.serializers.request.get_all import GetAllSerializer
from tracker_apps.meeting.serializers.request.get.meeting import MEETING_ID_ERRORS


class ActionItemGetSerializer(serializers.Serializer):
    action_item_id = fields.action_item_id_field()

    def create(self, validated_data: dict) -> ActionItemGet:
        return ActionItemGet(**validated_data)


class ActionItemGetAllSerializer(GetAllSerializer):
    allowed_sort_fields = ("due_date", "created_at", "updated_at", "priority", "status", "description", "owner_name")
    allowed_value_fields = tuple(ACTION_ITEM_COLUMNS)
    default_sort_by = "due_date"
    default_sort_order = "asc"

    meeting_id = serializers.IntegerField(min_value=1, required=False, default=None, error_messages=MEETING_ID_ERRORS)
    status = serializers.ChoiceField(choices=Status.values, required=False, default="", error_messages=fields.status_field().error_messages)
    priority = serializers.ChoiceField(choices=Priority.values, required=False, default="", error_messages=fields.priority_field().error_messages)
    owner = serializers.CharField(max_length=100, required=False, default="", allow_blank=True)
    is_overdue = serializers.BooleanField(required=False, allow_null=True, default=None)

    def create(self, validated_data: dict) -> ActionItemGetAll:
        return ActionItemGetAll(**validated_data)
