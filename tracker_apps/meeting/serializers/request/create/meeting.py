from rest_framework import serializers

from tracker_apps.meeting.dataclasses.request.create.meeting import MeetingCreate
from tracker_apps.meeting.serializers.request import fields


class MeetingCreateSerializer(serializers.Serializer):
    title = fields.title_field()
    meeting_date = fields.meeting_date_field()
    meeting_type = fields.meeting_type_field()
    participants = fields.participants_field()
    transcript = fields.transcript_field()
    notes = fields.notes_field()

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["participants"].required = False
        self.fields["notes"].required = False

    def validate_participants(self, value: list[str]) -> list[str]:
        return fields.clean_participants(value)

    def validate_notes(self, value: str) -> str:
        return fields.clean_notes(value)

    def create(self, validated_data: dict) -> MeetingCreate:
        return MeetingCreate(**validated_data)
