import json
import logging
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import RequestDataTooBig
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection
from django.http import Http404
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import path
from rest_framework import exceptions as drf_exceptions
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory

from tracker.constants import Constants
from tracker_apps.common.clock import Clock
from tracker_apps.common.common import Common
from tracker_apps.common.exceptions.http_errors import (
    ConflictErrors,
    ForbiddenErrors,
    NotFoundErrors,
    PayloadTooLargeErrors,
    UnsupportedMediaErrors,
)
from tracker_apps.common.exceptions.token_errors import TokenErrors
from tracker_apps.common.exceptions.validation_errors import ValidationErrors
from tracker_apps.common.serializer_validations import SerializerValidations
from tracker_apps.common.serializers.request.get_all import GetAllSerializer
from tracker_apps.common.serializers.response.api_response import ApiResponseSerializer
from tracker_apps.common.tests_utils import ApiTestCase
from tracker_apps.common.utils import Utils


class BootstrapSettingsTests(SimpleTestCase):
    def test_global_default_permission_is_is_authenticated(self) -> None:
        self.assertEqual(
            settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"],
            ("rest_framework.permissions.IsAuthenticated",),
        )

    def test_cors_does_not_allow_all_origins(self) -> None:
        self.assertFalse(settings.CORS_ALLOW_ALL_ORIGINS)
        self.assertNotIn("*", settings.ALLOWED_HOSTS)

    def test_ai_provider_defaults_to_mock(self) -> None:
        from tracker.config import Configurations

        self.assertEqual(Configurations.ai_provider, "mock")

    def test_jwt_uses_bearer_and_short_access_lifetime(self) -> None:
        self.assertEqual(settings.SIMPLE_JWT["AUTH_HEADER_TYPES"], ("Bearer",))
        self.assertEqual(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(), 15 * 60)


class BootstrapDatabaseTests(TestCase):
    def test_sqlite_connection_has_timeout_configured(self) -> None:
        self.assertEqual(settings.DATABASES["default"]["OPTIONS"]["timeout"], 20)
        self.assertEqual(connection.vendor, "sqlite")


class BootstrapUrlTests(TestCase):
    def test_schema_requires_auth_when_debug_is_off(self) -> None:
        self.assertEqual(APIClient().get("/api/schema/").status_code, 401)


class SampleGetAllSerializer(GetAllSerializer):
    allowed_sort_fields = ("created_at", "title")
    allowed_value_fields = ("title",)
    default_sort_by = "created_at"
    default_sort_order = "desc"


class SampleCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=20)
    participants = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    transcript_file = serializers.FileField(required=False)
    search_key = serializers.CharField(required=False, default="")

    def create(self, validated_data: dict):
        from types import SimpleNamespace

        return SimpleNamespace(**validated_data)


class SampleView:
    @Common(response_handler=ApiResponseSerializer).exception_handler
    def echo_extract(self, params) -> Response:
        data = {k: v for k, v in vars(params).items() if k not in ("transcript_file", "present_url")}
        data["has_file"] = getattr(params, "transcript_file", None) is not None
        return Response(data=Utils.success_response_data(message="ok", data=json.loads(json.dumps(data, default=str))))

    @Common().exception_handler
    def raise_extract(self, params) -> Response:
        raise RAISERS[params.kind]()

    @Common(response_handler=ApiResponseSerializer).exception_handler
    def bad_contract_extract(self, params) -> Response:
        return Response(data={"unexpected": True})


class KindSerializer(serializers.Serializer):
    kind = serializers.CharField(default="")

    def create(self, validated_data: dict):
        from types import SimpleNamespace

        return SimpleNamespace(**validated_data)


RAISERS = {
    "unknown": lambda: RuntimeError("secret /etc/passwd detail"),
    "validation": lambda: ValidationErrors([{"field": "title", "message": "Meeting title is required."}]),
    "token": lambda: TokenErrors(["Token expired"]),
    "notfound": lambda: NotFoundErrors(),
    "forbidden": lambda: ForbiddenErrors(),
    "conflict": lambda: ConflictErrors(["Analysis already running"]),
    "toolarge": lambda: PayloadTooLargeErrors(["File too large"]),
    "unsupported": lambda: UnsupportedMediaErrors(["Only .txt files are allowed"]),
    "http404": lambda: Http404("hidden"),
    "integrity": lambda: IntegrityError("UNIQUE constraint failed: secret_table.col"),
    "drf_permission": lambda: drf_exceptions.PermissionDenied("hidden"),
    "drf_throttled": lambda: drf_exceptions.Throttled(),
    "drf_validation": lambda: drf_exceptions.ValidationError({"email": ["Enter a valid email."]}),
    "datatoobig": lambda: RequestDataTooBig("hidden"),
}


@api_view(["GET"])
@SerializerValidations(serializer=SampleGetAllSerializer).validate
def sample_get_all(request: Request) -> Response:
    return SampleView().echo_extract(params=request.params)


@api_view(["POST", "PUT"])
@SerializerValidations(serializer=SampleCreateSerializer).validate
def sample_create(request: Request) -> Response:
    return SampleView().echo_extract(params=request.params)


@api_view(["GET"])
@SerializerValidations(serializer=KindSerializer).validate
def sample_raise(request: Request) -> Response:
    return SampleView().raise_extract(params=request.params)


@api_view(["GET"])
@SerializerValidations(serializer=KindSerializer).validate
def sample_bad_contract(request: Request) -> Response:
    return SampleView().bad_contract_extract(params=request.params)


@api_view(["GET"])
@permission_classes([AllowAny])
@SerializerValidations(serializer=KindSerializer).validate
def sample_public(request: Request) -> Response:
    return SampleView().echo_extract(params=request.params)


urlpatterns = [
    path("sample/get_all/", sample_get_all),
    path("sample/create/", sample_create),
    path("sample/raise/", sample_raise),
    path("sample/bad_contract/", sample_bad_contract),
    path("sample/public/", sample_public),
]


@override_settings(ROOT_URLCONF="tracker_apps.common.tests")
class CommonApiTestCase(ApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user()
        self.authenticate(self.user)


class UtilsEnvelopeTests(SimpleTestCase):
    def test_success_envelope_always_has_status_message_data(self) -> None:
        self.assertEqual(Utils.success_response_data("Done", {"a": 1}), {"status": True, "message": "Done", "data": {"a": 1}})
        self.assertEqual(Utils.success_response_data("Done"), {"status": True, "message": "Done", "data": None})

    def test_error_envelope_shape(self) -> None:
        self.assertEqual(Utils.error_response_data("Bad", ["x"]), {"status": False, "message": "Bad", "error": ["x"]})

    def test_flatten_errors_is_field_keyed(self) -> None:
        flat = Utils.flatten_errors({"title": ["Required."], "participants": {0: ["Bad."]}, "non_field_errors": ["Oops."]})
        self.assertIn({"field": "title", "message": "Required."}, flat)
        self.assertIn({"field": "participants.0", "message": "Bad."}, flat)
        self.assertIn({"field": "non_field_errors", "message": "Oops."}, flat)


class PaginationTests(TestCase):
    def test_single_page_has_no_navigation_urls(self) -> None:
        page = Utils.add_page_parameter([1, 2], 1, 1, "http://t/x/?a=1")
        self.assertEqual(page, {"data": [1, 2], "presentPage": 1, "totalPage": 1})

    def test_middle_page_has_next_and_previous_and_keeps_other_params(self) -> None:
        page = Utils.add_page_parameter([], 2, 3, "http://t/x/?search_key=quarterly%20review&page_num=2")
        self.assertEqual(page["nextPageUrl"], "http://t/x/?search_key=quarterly+review&page_num=3")
        self.assertEqual(page["previousPageUrl"], "http://t/x/?search_key=quarterly+review&page_num=1")

    def test_first_page_has_only_next_and_last_page_only_previous(self) -> None:
        first = Utils.add_page_parameter([], 1, 2, "http://t/x/")
        last = Utils.add_page_parameter([], 2, 2, "http://t/x/")
        self.assertIn("nextPageUrl", first)
        self.assertNotIn("previousPageUrl", first)
        self.assertIn("previousPageUrl", last)
        self.assertNotIn("nextPageUrl", last)

    def test_paginate_slices_and_counts(self) -> None:
        User = get_user_model()
        for index in range(5):
            User.objects.create_user(email=f"p{index}@example.com", name="P", password="x")
        rows, total_page = Utils.paginate(User.objects.order_by("email"), page_num=2, limit=2)
        self.assertEqual([row.email for row in rows], ["p2@example.com", "p3@example.com"])
        self.assertEqual(total_page, 3)

    def test_empty_queryset_is_one_empty_page_not_an_error(self) -> None:
        rows, total_page = Utils.paginate(get_user_model().objects.none(), page_num=1, limit=10)
        self.assertEqual((rows, total_page), ([], 1))

    def test_page_beyond_last_is_a_validation_error(self) -> None:
        with self.assertRaises(ValidationErrors) as caught:
            Utils.paginate(get_user_model().objects.none(), page_num=2, limit=10)
        self.assertEqual(caught.exception.errors[0]["field"], "page_num")


class ClockTests(SimpleTestCase):
    def test_override_sets_today_and_restores(self) -> None:
        real_today = Clock.today()
        with Clock.override(date(2026, 7, 28)):
            self.assertEqual(Clock.today(), date(2026, 7, 28))
            self.assertEqual(Clock.now().date(), date(2026, 7, 28))
        self.assertEqual(Clock.today(), real_today)


class ExceptionMappingTests(CommonApiTestCase):
    def raise_kind(self, kind: str):
        return self.client.get("/sample/raise/", {"kind": kind})

    def test_known_errors_map_to_expected_status(self) -> None:
        expected = {
            "validation": 400, "token": 401, "notfound": 404, "forbidden": 403, "conflict": 409,
            "toolarge": 413, "unsupported": 415, "http404": 404, "integrity": 409,
            "drf_permission": 403, "drf_throttled": 429, "drf_validation": 400, "datatoobig": 413,
        }
        for kind, http_status in expected.items():
            with self.subTest(kind=kind):
                self.assert_error_envelope(self.raise_kind(kind), http_status)

    def test_validation_error_is_field_keyed(self) -> None:
        body = self.assert_error_envelope(self.raise_kind("validation"), 400)
        self.assertEqual(body["error"], [{"field": "title", "message": "Meeting title is required."}])

    def test_drf_validation_error_is_flattened_to_field_keyed(self) -> None:
        body = self.assert_error_envelope(self.raise_kind("drf_validation"), 400)
        self.assertEqual(body["error"], [{"field": "email", "message": "Enter a valid email."}])

    def test_unknown_error_is_500_generic_and_logged(self) -> None:
        with self.assertLogs("tracker_apps.common.common", level="ERROR") as logs:
            body = self.assert_error_envelope(self.raise_kind("unknown"), 500)
        self.assertEqual(body["message"], Constants.server_error)
        self.assertEqual(body["error"], [Constants.server_error])
        self.assertIn("secret /etc/passwd detail", "\n".join(logs.output))

    @override_settings(DEBUG=True)
    def test_unknown_error_is_still_generic_500_when_debug_is_on(self) -> None:
        body = self.assert_error_envelope(self.raise_kind("unknown"), 500)
        self.assertEqual(body["message"], Constants.server_error)

    def test_responses_never_leak_internals(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        for kind in RAISERS:
            with self.subTest(kind=kind):
                text = self.raise_kind(kind).content.decode()
                for leaked in ("Traceback", "/etc/passwd", "secret_table", "hidden", "IntegrityError", "RuntimeError"):
                    self.assertNotIn(leaked, text)

    def test_response_contract_violation_is_500_not_a_leak(self) -> None:
        with self.assertLogs("tracker_apps.common.common", level="ERROR"):
            body = self.assert_error_envelope(self.client.get("/sample/bad_contract/"), 500)
        self.assertEqual(body["message"], Constants.server_error)

    def test_unauthenticated_request_gets_401_envelope(self) -> None:
        body = self.assert_error_envelope(APIClient().get("/sample/get_all/"), 401)
        self.assertEqual(body["message"], Constants.auth_error)

    def test_invalid_token_gets_401_envelope(self) -> None:
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        self.assert_error_envelope(client.get("/sample/get_all/"), 401)

    def test_malformed_json_body_is_400_envelope(self) -> None:
        response = self.client.post("/sample/create/", data="{bad", content_type="application/json")
        body = self.assert_error_envelope(response, 400)
        self.assertEqual(body["message"], Constants.malformed_body)

    def test_wrong_method_is_405_envelope(self) -> None:
        self.assert_error_envelope(self.client.delete("/sample/get_all/"), 405)

    def test_allow_any_endpoint_works_anonymously(self) -> None:
        self.assertEqual(APIClient().get("/sample/public/").status_code, 200)


class SerializerValidationsTests(CommonApiTestCase):
    def test_query_params_are_url_decoded(self) -> None:
        response = self.client.get("/sample/get_all/?search_key=quarterly%20review")
        self.assertEqual(response.json()["data"]["search_key"], "quarterly review")

    def test_query_value_containing_equals_survives(self) -> None:
        response = self.client.get("/sample/get_all/", {"search_key": "a=b"})
        self.assertEqual(response.json()["data"]["search_key"], "a=b")

    def test_per_resource_default_sort_is_applied(self) -> None:
        data = self.client.get("/sample/get_all/").json()["data"]
        self.assertEqual((data["sort_by"], data["sort_order"]), ("created_at", "desc"))
        self.assertEqual((data["page_num"], data["limit"]), (1, 10))

    def test_explicit_sort_overrides_default(self) -> None:
        data = self.client.get("/sample/get_all/", {"sort_by": "title", "sort_order": "asc"}).json()["data"]
        self.assertEqual((data["sort_by"], data["sort_order"]), ("title", "asc"))

    def test_unknown_sort_field_is_rejected_with_400(self) -> None:
        body = self.assert_error_envelope(self.client.get("/sample/get_all/", {"sort_by": "password"}), 400)
        self.assertEqual(body["error"][0]["field"], "sort_by")
        self.assertNotIn("password", body["error"][0]["message"].split("one of")[0])

    def test_unknown_values_column_is_rejected(self) -> None:
        self.assert_error_envelope(self.client.get("/sample/get_all/", {"values": "title,secret"}), 400)

    def test_bad_sort_order_page_and_limit_are_rejected(self) -> None:
        for query in ({"sort_order": "up"}, {"page_num": 0}, {"limit": 0}, {"limit": 100000}, {"page_num": "x"}):
            with self.subTest(query=query):
                self.assert_error_envelope(self.client.get("/sample/get_all/", query), 400)

    def test_iso_dates_accepted_and_two_digit_year_rejected(self) -> None:
        ok = self.client.get("/sample/get_all/", {"from_date": "2026-07-01", "to_date": "2026-07-31"})
        self.assertEqual(ok.json()["data"]["from_date"], "2026-07-01")
        self.assert_error_envelope(self.client.get("/sample/get_all/", {"from_date": "01-07-26"}), 400)

    def test_from_date_after_to_date_is_rejected(self) -> None:
        self.assert_error_envelope(self.client.get("/sample/get_all/", {"from_date": "2026-08-01", "to_date": "2026-07-01"}), 400)

    def test_params_carry_authenticated_user_id(self) -> None:
        self.assertEqual(self.client.get("/sample/get_all/").json()["data"]["user_id"], self.user.pk)

    def test_blank_query_values_are_ignored(self) -> None:
        self.assertEqual(self.client.get("/sample/get_all/?from_date=&search_key=").status_code, 200)

    def test_json_body_is_validated_with_field_keyed_errors(self) -> None:
        body = self.assert_error_envelope(self.client.post("/sample/create/", {"title": ""}, format="json"), 400)
        self.assertEqual(body["error"][0]["field"], "title")

    def test_json_array_body_is_rejected_not_crashed(self) -> None:
        self.assert_error_envelope(self.client.post("/sample/create/", [1, 2], format="json"), 400)

    def test_multipart_with_file_and_list_works(self) -> None:
        upload = SimpleUploadedFile("a.txt", b"hello", content_type="text/plain")
        response = self.client.post(
            "/sample/create/?search_key=from%20query",
            {"title": "Weekly", "transcript_file": upload, "participants": ["Ana", "Bo"]},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertTrue(data["has_file"])
        self.assertEqual(data["participants"], ["Ana", "Bo"])
        self.assertEqual(data["search_key"], "from query")

    def test_merge_does_not_mutate_request_data(self) -> None:
        raw = APIRequestFactory().post("/sample/create/?search_key=q", {"title": "T"}, format="multipart")
        request = Request(raw, parsers=[MultiPartParser()])
        keys_before = set(request.data.keys())
        merged = SerializerValidations(serializer=SampleCreateSerializer).merge_request_data(request)
        self.assertEqual(set(request.data.keys()), keys_before)
        self.assertEqual(merged["search_key"], "q")
        self.assertNotIn("search_key", request.data)

    def test_multipart_single_participant_stays_a_list(self) -> None:
        response = self.client.post("/sample/create/", {"title": "T", "participants": ["Ana"]}, format="multipart")
        self.assertEqual(response.json()["data"]["participants"], ["Ana"])

    def test_put_multipart_does_not_crash_on_immutable_querydict(self) -> None:
        response = self.client.put("/sample/create/", {"title": "T"}, format="multipart")
        self.assertEqual(response.status_code, 200)
