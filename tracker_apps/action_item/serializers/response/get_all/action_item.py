from rest_framework import serializers

from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer


class ActionItemListItemSerializer(serializers.Serializer):
    """Every field optional: `values=` may return a subset."""

    actionItemId = serializers.IntegerField(required=False)
    meetingId = serializers.IntegerField(required=False)
    meetingTitle = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    ownerName = serializers.CharField(allow_null=True, required=False)
    dueDate = serializers.DateField(allow_null=True, required=False)
    dueDateText = serializers.CharField(allow_null=True, required=False)
    priority = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    source = serializers.CharField(required=False)
    evidenceQuote = serializers.CharField(allow_null=True, required=False)
    isEdited = serializers.BooleanField(required=False)
    isOverdue = serializers.BooleanField(required=False)
    completedAt = serializers.DateTimeField(allow_null=True, required=False)
    createdAt = serializers.DateTimeField(required=False)
    updatedAt = serializers.DateTimeField(required=False)


class ActionItemPageSerializer(serializers.Serializer):
    data = ActionItemListItemSerializer(many=True)
    presentPage = serializers.IntegerField()
    totalPage = serializers.IntegerField()
    nextPageUrl = serializers.CharField(required=False)
    previousPageUrl = serializers.CharField(required=False)


class ActionItemListResponseSerializer(ApiResponseSerializer):
    data = ActionItemPageSerializer()
