from rest_framework import serializers

from tracker_apps.dashboard.dataclasses.request.get.dashboard import DashboardGet


class DashboardGetSerializer(serializers.Serializer):
    def create(self, validated_data: dict) -> DashboardGet:
        return DashboardGet()
