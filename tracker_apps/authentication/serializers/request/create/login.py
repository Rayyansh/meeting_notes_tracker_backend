from rest_framework import serializers

from tracker_apps.authentication.dataclasses.request.create.login import Login
from tracker_apps.authentication.models.user import UserManager
from tracker_apps.authentication.serializers.request.create.register import MAX_PASSWORD_LENGTH


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=MAX_PASSWORD_LENGTH, trim_whitespace=False, write_only=True)

    def create(self, validated_data: dict) -> Login:
        return Login(email=UserManager.normalize_email_address(validated_data["email"]), password=validated_data["password"])
