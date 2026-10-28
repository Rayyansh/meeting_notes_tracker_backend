from rest_framework import serializers

from tracker.config import Configurations
from tracker_apps.common.dataclasses.search import Search


class SearchSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=100, required=False, default="", allow_blank=True)
    page_num = serializers.IntegerField(min_value=1, default=1)
    limit = serializers.IntegerField(min_value=1, max_value=Configurations.max_page_size, default=Configurations.pagination_count)

    def create(self, validated_data: dict) -> Search:
        return Search(**validated_data)
