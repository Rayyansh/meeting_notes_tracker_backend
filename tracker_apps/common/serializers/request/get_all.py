from rest_framework import serializers

from tracker.config import Configurations
from tracker.constants import Constants
from tracker_apps.common.dataclasses.get_all import GetAll


class GetAllSerializer(serializers.Serializer):
    """Base list query. Subclasses set the whitelists and the per-resource default sort."""

    allowed_sort_fields: tuple[str, ...] = ()
    allowed_value_fields: tuple[str, ...] = ()
    default_sort_by: str = ""
    default_sort_order: str = "asc"

    values = serializers.CharField(max_length=100, required=False, default="", allow_blank=True)
    page_num = serializers.IntegerField(min_value=1, default=1)
    limit = serializers.IntegerField(min_value=1, max_value=Configurations.max_page_size, default=Configurations.pagination_count)
    sort_by = serializers.CharField(max_length=100, required=False, allow_blank=True)
    sort_order = serializers.ChoiceField(choices=["asc", "desc"], required=False)
    search_key = serializers.CharField(max_length=100, required=False, default="", allow_blank=True, trim_whitespace=True)
    from_date = serializers.DateField(required=False, default=None, help_text=Constants.iso_date_format)
    to_date = serializers.DateField(required=False, default=None, help_text=Constants.iso_date_format)

    def validate(self, attrs: dict) -> dict:
        attrs["sort_by"] = attrs.get("sort_by") or self.default_sort_by
        attrs["sort_order"] = attrs.get("sort_order") or self.default_sort_order
        if attrs["sort_by"] not in self.allowed_sort_fields:
            allowed = ", ".join(self.allowed_sort_fields)
            raise serializers.ValidationError({"sort_by": Constants.sort_by_invalid.format(allowed=allowed)})
        self.validate_value_fields(attrs["values"])
        if attrs["from_date"] and attrs["to_date"] and attrs["from_date"] > attrs["to_date"]:
            raise serializers.ValidationError({"from_date": Constants.date_range_invalid})
        return attrs

    def validate_value_fields(self, values: str) -> None:
        requested = [value for value in values.split(",") if value]
        if any(value not in self.allowed_value_fields for value in requested):
            allowed = ", ".join(self.allowed_value_fields)
            raise serializers.ValidationError({"values": Constants.values_invalid.format(allowed=allowed)})

    def create(self, validated_data: dict) -> GetAll:
        return GetAll(**validated_data)
