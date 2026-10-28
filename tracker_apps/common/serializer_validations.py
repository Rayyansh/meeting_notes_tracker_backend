from collections.abc import Callable, Mapping
from typing import Any

from django.http import QueryDict
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from tracker.constants import Constants
from tracker_apps.common.exceptions.validation_errors import ValidationErrors
from tracker_apps.common.utils import NON_FIELD, Utils


class SerializerValidations:
    def __init__(self, serializer: type[serializers.Serializer]) -> None:
        self.serializer = serializer

    def validate(self, func: Callable[..., Response]) -> Callable[..., Response]:
        def validator(*args: Any, **kwargs: Any) -> Response:
            request: Request = args[0]
            serializer = self.serializer(data=self.merge_request_data(request))
            if not serializer.is_valid():
                raise ValidationErrors(Utils.flatten_errors(serializer.errors))
            request.params = serializer.create(serializer.validated_data)
            request.params.user_id = request.user.pk
            if request.method == "GET":
                request.params.present_url = request.build_absolute_uri()
            return func(*args, **kwargs)

        validator.__name__ = func.__name__
        validator.__doc__ = func.__doc__
        return validator

    def merge_request_data(self, request: Request) -> dict:
        """Query string (already URL-decoded) overlaid with the body. Never mutates request.data."""
        list_fields = {name for name, field in self.serializer().fields.items() if isinstance(field, serializers.ListField)}
        merged = {key: value for key, value in self.query_dict_to_dict(request.query_params, list_fields).items() if value != ""}
        body = request.data
        if isinstance(body, QueryDict):
            merged.update(self.query_dict_to_dict(body, list_fields))
        elif isinstance(body, Mapping):
            merged.update(body)
        elif body:
            raise ValidationErrors([{"field": NON_FIELD, "message": Constants.invalid_body}])
        return merged

    @staticmethod
    def query_dict_to_dict(query_dict: QueryDict, list_fields: set[str]) -> dict:
        return {key: query_dict.getlist(key) if key in list_fields else query_dict.get(key) for key in query_dict}
