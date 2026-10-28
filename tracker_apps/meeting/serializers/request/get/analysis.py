from rest_framework import serializers

from tracker_apps.meeting.dataclasses.request.get.analysis import AnalysisGet
from tracker_apps.meeting.serializers.request.get.meeting import MEETING_ID_ERRORS


class AnalysisGetSerializer(serializers.Serializer):
    meeting_id = serializers.IntegerField(min_value=1, error_messages=MEETING_ID_ERRORS)

    def create(self, validated_data: dict) -> AnalysisGet:
        return AnalysisGet(**validated_data)
