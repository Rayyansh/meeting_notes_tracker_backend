from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from tracker.constants import Constants
from tracker_apps.authentication.dataclasses.request.create.register import Register
from tracker_apps.authentication.models.user import User, UserManager

MAX_PASSWORD_LENGTH = 128


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    name = serializers.CharField(max_length=100)
    password = serializers.CharField(max_length=MAX_PASSWORD_LENGTH, trim_whitespace=False, write_only=True)
    confirm_password = serializers.CharField(max_length=MAX_PASSWORD_LENGTH, trim_whitespace=False, write_only=True)

    def validate_email(self, value: str) -> str:
        if User.email_exists(value):
            raise serializers.ValidationError(Constants.email_unavailable)
        return UserManager.normalize_email_address(value)

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": Constants.password_mismatch})
        candidate = User(email=attrs["email"], name=attrs["name"])
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)})
        return attrs

    def create(self, validated_data: dict) -> Register:
        return Register(email=validated_data["email"], name=validated_data["name"], password=validated_data["password"])
