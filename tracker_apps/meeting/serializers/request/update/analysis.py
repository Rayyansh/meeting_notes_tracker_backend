from rest_framework import serializers

from tracker.constants import Constants
from tracker_apps.common.sanitizer import HtmlSanitizer
from tracker_apps.meeting.dataclasses.request.update.analysis import AnalysisUpdate
from tracker_apps.meeting.serializers.request import fields
from tracker_apps.meeting.serializers.request.get.meeting import MEETING_ID_ERRORS


class AnalysisUpdateSerializer(serializers.Serializer):
    """Only the summary is editable in v1; decisions, risks and the rest stay as the provider produced them."""

    meeting_id = serializers.IntegerField(min_value=1, error_messages=MEETING_ID_ERRORS)
    summary = serializers.CharField(
        max_length=Constants.summary_max_length,
        error_messages={"required": Constants.summary_required, "blank": Constants.summary_required, "max_length": Constants.summary_too_long},
    )
    created_at = fields.timestamp_field()
    updated_at = fields.timestamp_field()

    def validate_summary(self, value: str) -> str:
        cleaned = HtmlSanitizer.clean(value)
        if not cleaned:
            raise serializers.ValidationError(Constants.summary_required)
        return cleaned

    def create(self, validated_data: dict) -> AnalysisUpdate:
        return AnalysisUpdate(**validated_data)
