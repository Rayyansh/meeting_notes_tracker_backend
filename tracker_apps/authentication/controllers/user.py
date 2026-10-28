from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from tracker_apps.authentication.serializers.request.create.login import LoginSerializer
from tracker_apps.authentication.serializers.request.create.register import RegisterSerializer
from tracker_apps.authentication.serializers.request.create.token import TokenRefreshRequestSerializer
from tracker_apps.authentication.serializers.response.create.token import LoginResponseSerializer, TokenRefreshResponseSerializer
from tracker_apps.authentication.serializers.response.get.user import UserResponseSerializer
from tracker_apps.authentication.throttles import LoginRateThrottle, RegisterRateThrottle
from tracker_apps.authentication.views.user import UserView
from tracker_apps.common.serializer_validations import SerializerValidations
from tracker_apps.common.serializers.request.get import GetSerializer
from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer


class UserViewController:
    @staticmethod
    @extend_schema(request=RegisterSerializer, responses={201: UserResponseSerializer}, tags=["auth"])
    @api_view(["POST"])
    @permission_classes([AllowAny])
    @throttle_classes([RegisterRateThrottle])
    @SerializerValidations(serializer=RegisterSerializer).validate
    def register(request: Request) -> Response:
        return UserView().register_extract(params=request.params)

    @staticmethod
    @extend_schema(request=LoginSerializer, responses={200: LoginResponseSerializer}, tags=["auth"])
    @api_view(["POST"])
    @permission_classes([AllowAny])
    @throttle_classes([LoginRateThrottle])
    @SerializerValidations(serializer=LoginSerializer).validate
    def login(request: Request) -> Response:
        return UserView().login_extract(params=request.params)

    @staticmethod
    @extend_schema(request=TokenRefreshRequestSerializer, responses={200: ApiResponseSerializer}, tags=["auth"])
    @api_view(["POST"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=TokenRefreshRequestSerializer).validate
    def logout(request: Request) -> Response:
        return UserView().logout_extract(params=request.params)

    @staticmethod
    @extend_schema(request=TokenRefreshRequestSerializer, responses={200: TokenRefreshResponseSerializer}, tags=["auth"])
    @api_view(["POST"])
    @permission_classes([AllowAny])
    @throttle_classes([LoginRateThrottle])
    @SerializerValidations(serializer=TokenRefreshRequestSerializer).validate
    def token_refresh(request: Request) -> Response:
        return UserView().refresh_extract(params=request.params)

    @staticmethod
    @extend_schema(responses={200: UserResponseSerializer}, tags=["auth"])
    @api_view(["GET"])
    @permission_classes([IsAuthenticated])
    @SerializerValidations(serializer=GetSerializer).validate
    def me(request: Request) -> Response:
        return UserView().me_extract(params=request.params)
