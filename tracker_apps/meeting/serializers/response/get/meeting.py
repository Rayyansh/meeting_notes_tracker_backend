from rest_framework import serializers

from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer


class MeetingListItemSerializer(serializers.Serializer):
    meetingId = serializers.IntegerField(required=False)
    title = serializers.CharField(required=False)
    meetingDate = serializers.DateField(required=False)
    meetingType = serializers.CharField(required=False)
    participants = serializers.ListField(child=serializers.CharField(), required=False)
    analysisStatus = serializers.CharField(required=False)
    createdAt = serializers.DateTimeField(required=False)
    updatedAt = serializers.DateTimeField(required=False)


class MeetingDetailSerializer(MeetingListItemSerializer):
    transcript = serializers.CharField(required=False)
    transcriptSource = serializers.CharField(required=False)
    transcriptFilename = serializers.CharField(allow_null=True, required=False)
    notes = serializers.CharField(allow_blank=True, required=False)
    analysisErrorCode = serializers.CharField(allow_null=True, required=False)
    analyzedAt = serializers.DateTimeField(allow_null=True, required=False)
    transcriptChangedSinceAnalysis = serializers.BooleanField(required=False)


class MeetingResponseSerializer(ApiResponseSerializer):
    data = MeetingDetailSerializer()
