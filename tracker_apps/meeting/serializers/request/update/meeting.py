from rest_framework import serializers

from tracker.constants import Constants
from tracker_apps.meeting.dataclasses.request.update.meeting import MeetingUpdate
from tracker_apps.meeting.serializers.request import fields
from tracker_apps.meeting.serializers.request.transcript import TranscriptInputSerializer


class MeetingUpdateSerializer(TranscriptInputSerializer):
    require_transcript = False

    meeting_id = serializers.IntegerField(min_value=1, error_messages={"required": Constants.meeting_id_invalid, "invalid": Constants.meeting_id_invalid, "min_value": Constants.meeting_id_invalid})
    title = fields.title_field()
    meeting_date = fields.meeting_date_field()
    meeting_type = fields.meeting_type_field()
    participants = fields.participants_field()
    notes = fields.notes_field()
    created_at = fields.timestamp_field()
    updated_at = fields.timestamp_field()
    reset_analysis = serializers.BooleanField(default=False)

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        for name in ("title", "meeting_date", "meeting_type", "participants", "notes"):
            self.fields[name].required = False

    def validate(self, attrs: dict) -> dict:
        return self.resolve_transcript(attrs)

    def validate_participants(self, value: list[str]) -> list[str]:
        return fields.clean_participants(value)

    def validate_notes(self, value: str) -> str:
        return fields.clean_notes(value)

    def create(self, validated_data: dict) -> MeetingUpdate:
        return MeetingUpdate(**validated_data)
