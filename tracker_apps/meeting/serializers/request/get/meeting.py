from rest_framework import serializers

from tracker.constants import Constants
from tracker_apps.common.serializers.request.get_all import GetAllSerializer
from tracker_apps.meeting.choices import MeetingType
from tracker_apps.meeting.dataclasses.request.get.meeting import MeetingGet, MeetingGetAll
from tracker_apps.meeting.utils import MEETING_LIST_COLUMNS

MEETING_ID_ERRORS = {"required": Constants.meeting_id_invalid, "invalid": Constants.meeting_id_invalid, "min_value": Constants.meeting_id_invalid}


class MeetingGetSerializer(serializers.Serializer):
    meeting_id = serializers.IntegerField(min_value=1, error_messages=MEETING_ID_ERRORS)

    def create(self, validated_data: dict) -> MeetingGet:
        return MeetingGet(**validated_data)


class MeetingGetAllSerializer(GetAllSerializer):
    allowed_sort_fields = ("created_at", "updated_at", "meeting_date", "title")
    allowed_value_fields = tuple(MEETING_LIST_COLUMNS)
    default_sort_by = "created_at"
    default_sort_order = "desc"

    meeting_type = serializers.ChoiceField(
        choices=MeetingType.values,
        required=False,
        default="",
        error_messages={"invalid_choice": Constants.meeting_type_invalid.format(allowed=", ".join(MeetingType.values))},
    )

    def create(self, validated_data: dict) -> MeetingGetAll:
        return MeetingGetAll(**validated_data)
