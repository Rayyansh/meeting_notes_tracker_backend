from rest_framework import serializers

from tracker_apps.common.dataclasses.get import Get


class GetSerializer(serializers.Serializer):
    values = serializers.CharField(max_length=100, required=False, default="", allow_blank=True)

    def create(self, validated_data: dict) -> Get:
        return Get(**validated_data)
