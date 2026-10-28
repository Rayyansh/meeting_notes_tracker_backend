from rest_framework import serializers

from tracker_apps.action_item.serializers.response.get.action_item import ActionItemSerializer
from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer


class EvidenceItemSerializer(serializers.Serializer):
    text = serializers.CharField()
    evidence = serializers.CharField()


class AnalysisSerializer(serializers.Serializer):
    analysisId = serializers.IntegerField()
    summary = serializers.CharField()
    discussionPoints = serializers.ListField(child=serializers.CharField())
    decisions = EvidenceItemSerializer(many=True)
    risks = EvidenceItemSerializer(many=True)
    unansweredQuestions = EvidenceItemSerializer(many=True)
    providerName = serializers.CharField()
    providerModel = serializers.CharField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class AnalysisStateSerializer(serializers.Serializer):
    meetingId = serializers.IntegerField()
    analysisStatus = serializers.CharField()
    analysisErrorCode = serializers.CharField(allow_null=True)
    analyzedAt = serializers.DateTimeField(allow_null=True)
    transcriptChangedSinceAnalysis = serializers.BooleanField()
    analysis = AnalysisSerializer(allow_null=True)
    actionItems = ActionItemSerializer(many=True)


class AnalysisResponseSerializer(ApiResponseSerializer):
    data = AnalysisStateSerializer()
