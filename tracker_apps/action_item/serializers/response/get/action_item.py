from rest_framework import serializers


class ActionItemSerializer(serializers.Serializer):
    actionItemId = serializers.IntegerField()
    meetingId = serializers.IntegerField()
    description = serializers.CharField()
    ownerName = serializers.CharField(allow_null=True)
    dueDate = serializers.DateField(allow_null=True)
    dueDateText = serializers.CharField(allow_null=True)
    priority = serializers.CharField()
    status = serializers.CharField()
    source = serializers.CharField()
    evidenceQuote = serializers.CharField(allow_null=True)
    isEdited = serializers.BooleanField()
    completedAt = serializers.DateTimeField(allow_null=True)
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()
