from rest_framework import serializers

from tracker_apps.authentication.dataclasses.request.create.token import TokenRefresh


class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(max_length=2048, write_only=True)

    def create(self, validated_data: dict) -> TokenRefresh:
        return TokenRefresh(refresh=validated_data["refresh"])
