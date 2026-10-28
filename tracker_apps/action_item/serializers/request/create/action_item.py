from rest_framework import serializers

from tracker_apps.action_item.dataclasses.request.create.action_item import ActionItemCreate
from tracker_apps.action_item.serializers.request import fields
from tracker_apps.meeting.serializers.request.get.meeting import MEETING_ID_ERRORS


class ActionItemCreateSerializer(serializers.Serializer):
    meeting_id = serializers.IntegerField(min_value=1, error_messages=MEETING_ID_ERRORS)
    description = fields.description_field()
    owner_name = fields.owner_name_field()
    due_date = fields.due_date_field()
    due_date_text = fields.due_date_text_field()
    priority = fields.priority_field()
    status = fields.status_field()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        for name in ("owner_name", "due_date", "due_date_text", "priority", "status"):
            self.fields[name].required = False

    def create(self, validated_data: dict) -> ActionItemCreate:
        return ActionItemCreate(**validated_data)
