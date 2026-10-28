from rest_framework import serializers

from tracker.constants import Constants
from tracker_apps.action_item.dataclasses.request.update.action_item import ActionItemUpdate
from tracker_apps.action_item.serializers.request import fields
from tracker_apps.common.exceptions.validation_errors import ValidationErrors

UPDATABLE = ("description", "owner_name", "due_date", "due_date_text", "priority", "status")


class ActionItemUpdateSerializer(serializers.Serializer):
    action_item_id = fields.action_item_id_field()
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
        for name in UPDATABLE:
            self.fields[name].required = False

    def validate(self, attrs: dict) -> dict:
        if not any(name in attrs for name in UPDATABLE):
            raise ValidationErrors([{"field": "action_item_id", "message": Constants.action_nothing_to_update}])
        return attrs

    def create(self, validated_data: dict) -> ActionItemUpdate:
        provided = frozenset(name for name in UPDATABLE if name in validated_data)
        return ActionItemUpdate(provided=provided, **validated_data)
