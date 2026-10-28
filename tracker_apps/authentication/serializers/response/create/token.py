from rest_framework import serializers

from tracker_apps.authentication.serializers.response.get.user import UserSerializer
from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer


class LoginDataSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class LoginResponseSerializer(ApiResponseSerializer):
    data = LoginDataSerializer()


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class TokenRefreshResponseSerializer(ApiResponseSerializer):
    data = TokenPairSerializer()
