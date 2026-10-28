from rest_framework import serializers

from tracker.config import Configurations
from tracker.constants import Constants
from tracker_apps.common.sanitizer import HtmlSanitizer
from tracker_apps.meeting.choices import MeetingType


def title_field() -> serializers.CharField:
    return serializers.CharField(
        max_length=Constants.title_max_length,
        error_messages={"required": Constants.title_required, "blank": Constants.title_required, "max_length": Constants.title_too_long},
    )


def meeting_date_field() -> serializers.DateField:
    return serializers.DateField(error_messages={"required": Constants.meeting_date_required, "invalid": Constants.meeting_date_invalid})


def meeting_type_field() -> serializers.ChoiceField:
    allowed = ", ".join(MeetingType.values)
    return serializers.ChoiceField(
        choices=MeetingType.values,
        error_messages={"required": Constants.meeting_type_invalid.format(allowed=allowed), "invalid_choice": Constants.meeting_type_invalid.format(allowed=allowed)},
    )


def participants_field() -> serializers.ListField:
    return serializers.ListField(
        child=serializers.CharField(max_length=Constants.participant_max_length, allow_blank=True),
        max_length=Constants.participants_max_count,
        error_messages={"not_a_list": Constants.participants_invalid, "max_length": Constants.participants_invalid},
    )


def transcript_field() -> serializers.CharField:
    return serializers.CharField(
        max_length=Configurations.upload_max_bytes,
        error_messages={"required": Constants.transcript_required, "blank": Constants.transcript_required, "max_length": Constants.transcript_too_long},
    )


def notes_field() -> serializers.CharField:
    return serializers.CharField(
        max_length=Constants.notes_max_length, allow_blank=True, error_messages={"max_length": Constants.notes_too_long}
    )


def clean_participants(names: list[str]) -> list[str]:
    """Trim, drop blanks, and de-duplicate case-insensitively while keeping first-seen order."""
    seen: set[str] = set()
    cleaned: list[str] = []
    for name in (name.strip() for name in names):
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            cleaned.append(name)
    return cleaned


def clean_notes(html: str) -> str:
    return HtmlSanitizer.clean(html)


def timestamp_field() -> serializers.DateTimeField:
    """created_at / updated_at: shown in the API schema, never accepted from a client."""
    return serializers.DateTimeField(read_only=True)
