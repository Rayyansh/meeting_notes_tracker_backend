from rest_framework import serializers

from tracker_apps.action_item.dataclasses.request.delete.action_item import ActionItemDelete
from tracker_apps.action_item.serializers.request import fields


class ActionItemDeleteSerializer(serializers.Serializer):
    action_item_id = fields.action_item_id_field()

    def create(self, validated_data: dict) -> ActionItemDelete:
        return ActionItemDelete(**validated_data)
