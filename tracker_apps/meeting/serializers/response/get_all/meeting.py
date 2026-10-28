from rest_framework import serializers

from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer
from tracker_apps.meeting.serializers.response.get.meeting import MeetingListItemSerializer


class MeetingPageSerializer(serializers.Serializer):
    data = MeetingListItemSerializer(many=True)
    presentPage = serializers.IntegerField()
    totalPage = serializers.IntegerField()
    nextPageUrl = serializers.CharField(required=False)
    previousPageUrl = serializers.CharField(required=False)


class MeetingListResponseSerializer(ApiResponseSerializer):
    data = MeetingPageSerializer()
