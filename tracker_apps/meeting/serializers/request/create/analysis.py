from rest_framework import serializers

from tracker_apps.meeting.dataclasses.request.create.analysis import AnalysisCreate
from tracker_apps.meeting.serializers.request.get.meeting import MEETING_ID_ERRORS


class AnalysisCreateSerializer(serializers.Serializer):
    meeting_id = serializers.IntegerField(min_value=1, error_messages=MEETING_ID_ERRORS)

    def create(self, validated_data: dict) -> AnalysisCreate:
        return AnalysisCreate(**validated_data)
