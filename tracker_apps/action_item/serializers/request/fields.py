from rest_framework import serializers

from tracker.constants import Constants
from tracker_apps.action_item.choices import Priority, Status

ACTION_ITEM_ID_ERRORS = {
    "required": Constants.action_item_id_invalid,
    "invalid": Constants.action_item_id_invalid,
    "min_value": Constants.action_item_id_invalid,
}


def action_item_id_field() -> serializers.IntegerField:
    return serializers.IntegerField(min_value=1, error_messages=ACTION_ITEM_ID_ERRORS)


def description_field() -> serializers.CharField:
    return serializers.CharField(
        max_length=Constants.action_description_max_length,
        error_messages={
            "required": Constants.action_description_required,
            "blank": Constants.action_description_required,
            "max_length": Constants.action_description_too_long,
        },
    )


def owner_name_field() -> serializers.CharField:
    return serializers.CharField(
        max_length=Constants.action_owner_max_length, allow_blank=True, error_messages={"max_length": Constants.action_owner_too_long}
    )


def due_date_field() -> serializers.DateField:
    return serializers.DateField(allow_null=True, error_messages={"invalid": Constants.action_due_date_invalid})


def due_date_text_field() -> serializers.CharField:
    return serializers.CharField(
        max_length=Constants.action_due_text_max_length, allow_blank=True, error_messages={"max_length": Constants.action_due_text_too_long}
    )


def priority_field() -> serializers.ChoiceField:
    message = Constants.action_priority_invalid.format(allowed=", ".join(Priority.values))
    return serializers.ChoiceField(choices=Priority.values, error_messages={"invalid_choice": message})


def status_field() -> serializers.ChoiceField:
    message = Constants.action_status_invalid.format(allowed=", ".join(Status.values))
    return serializers.ChoiceField(choices=Status.values, error_messages={"invalid_choice": message})
