from rest_framework import serializers

from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer


class ActionItemSerializer(serializers.Serializer):
    actionItemId = serializers.IntegerField()
    meetingId = serializers.IntegerField()
    meetingTitle = serializers.CharField()
    description = serializers.CharField()
    ownerName = serializers.CharField(allow_null=True)
    dueDate = serializers.DateField(allow_null=True)
    dueDateText = serializers.CharField(allow_null=True)
    priority = serializers.CharField()
    status = serializers.CharField()
    source = serializers.CharField()
    evidenceQuote = serializers.CharField(allow_null=True)
    isEdited = serializers.BooleanField()
    isOverdue = serializers.BooleanField()
    completedAt = serializers.DateTimeField(allow_null=True)
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class ActionItemResponseSerializer(ApiResponseSerializer):
    data = ActionItemSerializer()
