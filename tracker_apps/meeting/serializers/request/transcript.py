from rest_framework import serializers

from tracker.constants import Constants
from tracker_apps.common.exceptions.validation_errors import ValidationErrors
from tracker_apps.meeting.choices import TranscriptSource
from tracker_apps.meeting.serializers.request import fields
from tracker_apps.meeting.transcript import FILE_FIELD, TEXT_FIELD, TranscriptValidator


class TranscriptInputSerializer(serializers.Serializer):
    """Shared by create and update: exactly one of pasted text or a .txt upload."""

    require_transcript: bool = True

    transcript = fields.transcript_field()
    transcript_file = serializers.FileField(required=False, allow_empty_file=True, write_only=True)

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["transcript"].required = False

    def validate_transcript(self, value: str) -> str:
        return TranscriptValidator.validate_text(value, TEXT_FIELD)

    def resolve_transcript(self, attrs: dict) -> dict:
        has_text, has_file = TEXT_FIELD in attrs, FILE_FIELD in attrs
        if has_text and has_file:
            raise ValidationErrors([{"field": TEXT_FIELD, "message": Constants.transcript_both}])
        if has_file:
            text, name = TranscriptValidator.from_upload(attrs.pop(FILE_FIELD))
            attrs.update(transcript=text, transcript_source=TranscriptSource.FILE, transcript_filename=name)
        elif has_text:
            attrs.update(transcript_source=TranscriptSource.TEXT, transcript_filename=None)
        elif self.require_transcript:
            raise ValidationErrors([{"field": TEXT_FIELD, "message": Constants.transcript_required}])
        return attrs
