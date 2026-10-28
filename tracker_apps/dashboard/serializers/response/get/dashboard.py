from rest_framework import serializers

from tracker_apps.action_item.serializers.response.get.action_item import ActionItemSerializer
from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer
from tracker_apps.meeting.serializers.response.get.meeting import MeetingListItemSerializer


class PriorityCountsSerializer(serializers.Serializer):
    Low = serializers.IntegerField()
    Medium = serializers.IntegerField()
    High = serializers.IntegerField()


class DashboardSummarySerializer(serializers.Serializer):
    totalMeetings = serializers.IntegerField()
    totalActionItems = serializers.IntegerField()
    openActionItems = serializers.IntegerField()
    inProgressActionItems = serializers.IntegerField()
    blockedActionItems = serializers.IntegerField()
    completedActionItems = serializers.IntegerField()
    unfinishedActionItems = serializers.IntegerField()
    overdueActionItems = serializers.IntegerField()
    actionItemsByPriority = PriorityCountsSerializer()
    recentMeetings = MeetingListItemSerializer(many=True)
    upcomingActionItems = ActionItemSerializer(many=True)


class DashboardResponseSerializer(ApiResponseSerializer):
    data = DashboardSummarySerializer()
