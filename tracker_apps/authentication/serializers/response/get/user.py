from rest_framework import serializers

from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer


class UserSerializer(serializers.Serializer):
    userId = serializers.IntegerField()
    email = serializers.EmailField()
    name = serializers.CharField()
    createdAt = serializers.DateTimeField()


class UserResponseSerializer(ApiResponseSerializer):
    data = UserSerializer()
