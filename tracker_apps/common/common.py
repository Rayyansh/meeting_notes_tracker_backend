import logging
from collections.abc import Callable
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, RequestDataTooBig, TooManyFieldsSent
from django.db import IntegrityError
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError

from tracker.constants import Constants
from tracker_apps.common.exceptions.http_errors import (
    ConflictErrors,
    ForbiddenErrors,
    HttpErrors,
    NotFoundErrors,
    PayloadTooLargeErrors,
    UnsupportedMediaErrors,
)
from tracker_apps.common.exceptions.token_errors import TokenErrors
from tracker_apps.common.exceptions.validation_errors import ValidationErrors
from tracker_apps.common.utils import Utils

logger = logging.getLogger(__name__)

HTTP_ERROR_MAP: list[tuple[type[Exception], int, str]] = [
    (NotFoundErrors, status.HTTP_404_NOT_FOUND, Constants.item_not_found),
    (ForbiddenErrors, status.HTTP_403_FORBIDDEN, Constants.not_permitted),
    (ConflictErrors, status.HTTP_409_CONFLICT, Constants.conflict),
    (PayloadTooLargeErrors, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, Constants.payload_too_large),
    (UnsupportedMediaErrors, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, Constants.unsupported_media),
]


def error_response(http_status: int, message: str, error: list) -> Response:
    return Response(status=http_status, data=Utils.error_response_data(message=message, error=error))


def known_error_response(exc: Exception) -> Response | None:
    """Map an expected exception to a safe response, or None if it is not a known one."""
    if isinstance(exc, ValidationErrors):
        return error_response(status.HTTP_400_BAD_REQUEST, Constants.validation_error, exc.errors)
    if isinstance(exc, drf_exceptions.ValidationError):
        errors = Utils.flatten_errors(exc.detail)
        return error_response(status.HTTP_400_BAD_REQUEST, Constants.validation_error, errors)
    if isinstance(exc, (TokenErrors, drf_exceptions.NotAuthenticated, drf_exceptions.AuthenticationFailed, TokenError)):
        errors = exc.errors if isinstance(exc, TokenErrors) else [Constants.unauthorized]
        return error_response(status.HTTP_401_UNAUTHORIZED, Constants.auth_error, errors)
    for exc_type, http_status, message in HTTP_ERROR_MAP:
        if isinstance(exc, exc_type):
            return error_response(http_status, message, exc.errors or [message])
    return known_framework_error_response(exc)


def known_framework_error_response(exc: Exception) -> Response | None:
    if isinstance(exc, (Http404, ObjectDoesNotExist, drf_exceptions.NotFound)):
        return error_response(status.HTTP_404_NOT_FOUND, Constants.item_not_found, [Constants.item_not_found])
    if isinstance(exc, (drf_exceptions.PermissionDenied, ForbiddenErrors)):
        return error_response(status.HTTP_403_FORBIDDEN, Constants.not_permitted, [Constants.not_permitted])
    if isinstance(exc, drf_exceptions.Throttled):
        return error_response(status.HTTP_429_TOO_MANY_REQUESTS, Constants.rate_limited, [Constants.rate_limited])
    if isinstance(exc, drf_exceptions.MethodNotAllowed):
        return error_response(status.HTTP_405_METHOD_NOT_ALLOWED, Constants.method_not_allowed, [Constants.method_not_allowed])
    if isinstance(exc, drf_exceptions.UnsupportedMediaType):
        return error_response(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, Constants.unsupported_media, [Constants.unsupported_media])
    if isinstance(exc, RequestDataTooBig):
        return error_response(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, Constants.payload_too_large, [Constants.payload_too_large])
    if isinstance(exc, (drf_exceptions.ParseError, TooManyFieldsSent)):
        return error_response(status.HTTP_400_BAD_REQUEST, Constants.malformed_body, [Constants.malformed_body])
    if isinstance(exc, IntegrityError):
        logger.warning("Integrity error mapped to 409: %s", type(exc).__name__)
        return error_response(status.HTTP_409_CONFLICT, Constants.conflict, [Constants.conflict])
    return None


def server_error_response(exc: Exception) -> Response:
    """Unknown failure: full detail goes to the server log only; the client gets a generic 500."""
    logger.error("Unhandled exception", exc_info=exc)
    return error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, Constants.server_error, [Constants.server_error])


def map_exception(exc: Exception) -> Response:
    return known_error_response(exc) or server_error_response(exc)


def drf_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """DRF EXCEPTION_HANDLER: keeps auth/permission/parse errors in the same envelope."""
    return map_exception(exc)


class Common:
    def __init__(self, response_handler: type | None = None) -> None:
        self.response_handler = response_handler

    def exception_handler(self, func: Callable[..., Response]) -> Callable[..., Response]:
        def exceptions(*args: Any, **kwargs: Any) -> Response:
            try:
                response = func(*args, **kwargs)
                self.check_response_contract(response)
            except Exception as exc:  # central handler: the one allowed broad catch
                return map_exception(exc)
            return response

        exceptions.__name__ = func.__name__
        exceptions.__doc__ = func.__doc__
        return exceptions

    def check_response_contract(self, response: Response) -> None:
        if self.response_handler is None:
            return
        serializer = self.response_handler(data=response.data)
        if not serializer.is_valid():
            raise RuntimeError(f"Response failed {self.response_handler.__name__} contract: {dict(serializer.errors)}")

