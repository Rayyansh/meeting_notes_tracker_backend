import logging

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication as SimpleJWTAuthentication

logger = logging.getLogger(__name__)


class JWTAuthentication(SimpleJWTAuthentication):
    """simplejwt bearer auth that logs failures (never the token) before DRF turns them into a 401."""

    def authenticate(self, request: Request) -> tuple | None:
        try:
            return super().authenticate(request)
        except AuthenticationFailed:
            logger.warning("Access token rejected")
            raise
