import logging

from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from tracker.constants import Constants
from tracker_apps.authentication.dataclasses.request.create.login import Login
from tracker_apps.authentication.dataclasses.request.create.register import Register
from tracker_apps.authentication.dataclasses.request.create.token import TokenRefresh
from tracker_apps.authentication.models.user import User
from tracker_apps.authentication.serializers.response.create.token import LoginResponseSerializer, TokenRefreshResponseSerializer
from tracker_apps.authentication.serializers.response.get.user import UserResponseSerializer
from tracker_apps.authentication.utils import AuthUtils
from tracker_apps.common.common import Common
from tracker_apps.common.dataclasses.get import Get
from tracker_apps.common.exceptions.token_errors import TokenErrors
from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer
from tracker_apps.common.utils import Utils

logger = logging.getLogger(__name__)


class UserView:
    def __init__(self) -> None:
        self.register_success = Constants.register_success
        self.login_success = Constants.login_success
        self.logout_success = Constants.logout_success
        self.refresh_success = Constants.refresh_success
        self.data_get = Constants.data_get

    @Common(response_handler=UserResponseSerializer).exception_handler
    def register_extract(self, params: Register) -> Response:
        with transaction.atomic():
            user = User.create(email=params.email, name=params.name, password=params.password)
        return Response(
            status=status.HTTP_201_CREATED,
            data=Utils.success_response_data(message=self.register_success, data=AuthUtils.user_response(user)),
        )

    @Common(response_handler=LoginResponseSerializer).exception_handler
    def login_extract(self, params: Login) -> Response:
        user = authenticate(email=params.email, password=params.password)
        if user is None:
            logger.warning(Constants.login_failed_log)
            raise TokenErrors([Constants.invalid_credentials])
        refresh = RefreshToken.for_user(user)
        data = {"access": str(refresh.access_token), "refresh": str(refresh), "user": AuthUtils.user_response(user)}
        return Response(status=status.HTTP_200_OK, data=Utils.success_response_data(message=self.login_success, data=data))

    @Common(response_handler=ApiResponseSerializer).exception_handler
    def logout_extract(self, params: TokenRefresh) -> Response:
        refresh = RefreshToken(params.refresh)
        if str(refresh["user_id"]) != str(params.user_id):
            raise TokenErrors([Constants.refresh_not_owned])
        refresh.blacklist()
        return Response(status=status.HTTP_200_OK, data=Utils.success_response_data(message=self.logout_success))

    @Common(response_handler=TokenRefreshResponseSerializer).exception_handler
    def refresh_extract(self, params: TokenRefresh) -> Response:
        serializer = TokenRefreshSerializer(data={"refresh": params.refresh})
        serializer.is_valid(raise_exception=True)
        data = {"access": serializer.validated_data["access"], "refresh": serializer.validated_data["refresh"]}
        return Response(status=status.HTTP_200_OK, data=Utils.success_response_data(message=self.refresh_success, data=data))

    @Common(response_handler=UserResponseSerializer).exception_handler
    def me_extract(self, params: Get) -> Response:
        user = User.get(user_id=params.user_id)
        return Response(
            status=status.HTTP_200_OK,
            data=Utils.success_response_data(message=self.data_get, data=AuthUtils.user_response(user)),
        )
