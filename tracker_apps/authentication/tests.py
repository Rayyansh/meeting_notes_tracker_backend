from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from tracker.constants import Constants
from tracker_apps.authentication.throttles import LoginRateThrottle, RegisterRateThrottle
from tracker_apps.common.tests_utils import TEST_PASSWORD, ApiTestCase

REGISTER_URL = "/auth/register/"
LOGIN_URL = "/auth/login/"
LOGOUT_URL = "/auth/logout/"
REFRESH_URL = "/auth/token/refresh/"
ME_URL = "/auth/me/"


class AuthApiTestCase(ApiTestCase):
    def register_payload(self, **overrides: str) -> dict:
        payload = {"email": "New.User@Example.com", "name": "New User", "password": TEST_PASSWORD, "confirm_password": TEST_PASSWORD}
        payload.update(overrides)
        return payload

    def login(self, email: str = "user@example.com", password: str = TEST_PASSWORD):
        return self.client.post(LOGIN_URL, {"email": email, "password": password}, format="json")

    def login_tokens(self, user=None) -> dict:
        user = user or self.create_user()
        return self.assert_success_envelope(self.login(user.email))["data"]

    def bearer(self, access: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")


class RegisterTests(AuthApiTestCase):
    def test_register_creates_user_with_camel_case_response_and_no_secrets(self) -> None:
        response = self.client.post(REGISTER_URL, self.register_payload(), format="json")
        body = self.assert_success_envelope(response, 201)
        self.assertEqual(set(body["data"]), {"userId", "email", "name", "createdAt"})
        self.assertEqual(body["data"]["email"], "new.user@example.com")
        self.assertNotIn(TEST_PASSWORD, response.content.decode())
        self.assertNotIn("password", response.content.decode().lower())

    def test_password_is_stored_hashed(self) -> None:
        self.client.post(REGISTER_URL, self.register_payload(), format="json")
        user = get_user_model().objects.get(email="new.user@example.com")
        self.assertNotEqual(user.password, TEST_PASSWORD)
        self.assertIn("$", user.password)
        self.assertTrue(user.check_password(TEST_PASSWORD))

    def test_duplicate_email_is_rejected_case_insensitively_with_neutral_message(self) -> None:
        self.create_user(email="taken@example.com")
        response = self.client.post(REGISTER_URL, self.register_payload(email="TAKEN@example.com"), format="json")
        body = self.assert_error_envelope(response, 400)
        self.assertEqual(body["error"], [{"field": "email", "message": Constants.email_unavailable}])
        self.assertNotIn("already", response.content.decode().lower())

    def test_password_mismatch_is_field_keyed(self) -> None:
        body = self.assert_error_envelope(
            self.client.post(REGISTER_URL, self.register_payload(confirm_password="Different-1!"), format="json"), 400
        )
        self.assertEqual(body["error"][0]["field"], "confirm_password")

    def test_weak_passwords_are_rejected_by_django_validators(self) -> None:
        for weak in ("short1!", "password", "12345678901", "new.user@example.com"):
            with self.subTest(password=weak):
                payload = self.register_payload(password=weak, confirm_password=weak)
                body = self.assert_error_envelope(self.client.post(REGISTER_URL, payload, format="json"), 400)
                self.assertEqual(body["error"][0]["field"], "password")

    def test_missing_and_invalid_fields_are_rejected(self) -> None:
        for payload in ({}, self.register_payload(email="not-an-email"), self.register_payload(name="  ")):
            with self.subTest(payload=payload):
                self.assert_error_envelope(self.client.post(REGISTER_URL, payload, format="json"), 400)
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_register_is_throttled(self) -> None:
        with patch.dict(RegisterRateThrottle.THROTTLE_RATES, {"register": "2/min"}):
            statuses = [self.client.post(REGISTER_URL, {}, format="json").status_code for _ in range(3)]
        self.assertEqual(statuses, [400, 400, 429])


class LoginTests(AuthApiTestCase):
    def test_login_returns_tokens_and_user_without_password(self) -> None:
        user = self.create_user()
        response = self.login()
        data = self.assert_success_envelope(response)["data"]
        self.assertEqual(set(data), {"access", "refresh", "user"})
        self.assertEqual(data["user"]["userId"], user.user_id)
        self.assertNotIn(TEST_PASSWORD, response.content.decode())

    def test_login_email_is_case_insensitive(self) -> None:
        self.create_user(email="user@example.com")
        self.assert_success_envelope(self.login(email="USER@Example.com"))

    def test_unknown_email_and_wrong_password_are_indistinguishable(self) -> None:
        self.create_user()
        unknown = self.login(email="nobody@example.com")
        wrong = self.login(password="Wrong-Passw0rd!")
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(unknown.json(), wrong.json())
        self.assertEqual(wrong.json()["error"], [Constants.invalid_credentials])

    def test_inactive_user_cannot_log_in_and_gets_same_error(self) -> None:
        user = self.create_user()
        user.is_active = False
        user.save()
        self.assertEqual(self.login().json(), self.login(email="nobody@example.com").json())

    def test_failed_login_is_logged_without_email_or_password(self) -> None:
        self.create_user()
        with self.assertLogs("tracker_apps.authentication.views.user", level="WARNING") as logs:
            self.login(password="Wrong-Passw0rd!")
        text = "\n".join(logs.output)
        self.assertNotIn("user@example.com", text)
        self.assertNotIn("Wrong-Passw0rd!", text)

    def test_bad_login_payload_is_400(self) -> None:
        self.assert_error_envelope(self.client.post(LOGIN_URL, {"email": "x"}, format="json"), 400)

    def test_login_is_throttled(self) -> None:
        self.create_user()
        with patch.dict(LoginRateThrottle.THROTTLE_RATES, {"login": "2/min"}):
            statuses = [self.login(password="Wrong-Passw0rd!").status_code for _ in range(3)]
            throttled = self.login()
        self.assertEqual(statuses, [401, 401, 429])
        self.assert_error_envelope(throttled, 429)


class MeAndProtectionTests(AuthApiTestCase):
    def test_me_returns_current_user_with_access_token(self) -> None:
        tokens = self.login_tokens()
        self.bearer(tokens["access"])
        data = self.assert_success_envelope(self.client.get(ME_URL))["data"]
        self.assertEqual(data["email"], "user@example.com")

    def test_me_requires_authentication(self) -> None:
        self.assert_error_envelope(self.client.get(ME_URL), 401)

    def test_garbage_and_wrong_scheme_tokens_are_401(self) -> None:
        for header in ("Bearer garbage", "Token abc", "Bearer"):
            with self.subTest(header=header):
                self.client.credentials(HTTP_AUTHORIZATION=header)
                self.assert_error_envelope(self.client.get(ME_URL), 401)

    def test_refresh_token_is_not_accepted_as_access_token(self) -> None:
        tokens = self.login_tokens()
        self.bearer(tokens["refresh"])
        self.assert_error_envelope(self.client.get(ME_URL), 401)

    def test_expired_access_token_is_401(self) -> None:
        user = self.create_user()
        token = AccessToken.for_user(user)
        token.set_exp(lifetime=-timedelta(seconds=5))
        self.bearer(str(token))
        self.assert_error_envelope(self.client.get(ME_URL), 401)

    def test_access_token_of_deactivated_user_is_401(self) -> None:
        user = self.create_user()
        self.bearer(self.login_tokens(user)["access"])
        user.is_active = False
        user.save()
        self.assert_error_envelope(self.client.get(ME_URL), 401)

    def test_rejected_token_is_logged_without_the_token(self) -> None:
        self.bearer("secret-looking-garbage")
        with self.assertLogs("tracker_apps.authentication.authentication", level="WARNING") as logs:
            self.client.get(ME_URL)
        self.assertNotIn("secret-looking-garbage", "\n".join(logs.output))


class LogoutAndRefreshTests(AuthApiTestCase):
    def test_logout_blacklists_refresh_token(self) -> None:
        tokens = self.login_tokens()
        self.bearer(tokens["access"])
        self.assert_success_envelope(self.client.post(LOGOUT_URL, {"refresh": tokens["refresh"]}, format="json"))
        self.assertEqual(BlacklistedToken.objects.count(), 1)
        self.client.credentials()
        self.assert_error_envelope(self.client.post(REFRESH_URL, {"refresh": tokens["refresh"]}, format="json"), 401)

    def test_logout_requires_authentication(self) -> None:
        tokens = self.login_tokens()
        self.assert_error_envelope(self.client.post(LOGOUT_URL, {"refresh": tokens["refresh"]}, format="json"), 401)
        self.assertEqual(BlacklistedToken.objects.count(), 0)

    def test_logout_with_missing_or_garbage_refresh_is_rejected(self) -> None:
        self.bearer(self.login_tokens()["access"])
        self.assert_error_envelope(self.client.post(LOGOUT_URL, {}, format="json"), 400)
        self.assert_error_envelope(self.client.post(LOGOUT_URL, {"refresh": "garbage"}, format="json"), 401)

    def test_user_cannot_blacklist_another_users_refresh_token(self) -> None:
        mine = self.login_tokens(self.create_user(email="a@example.com"))
        theirs = self.login_tokens(self.create_user(email="b@example.com"))
        self.bearer(mine["access"])
        self.assert_error_envelope(self.client.post(LOGOUT_URL, {"refresh": theirs["refresh"]}, format="json"), 401)
        self.assertEqual(BlacklistedToken.objects.count(), 0)

    def test_second_logout_with_same_refresh_is_rejected(self) -> None:
        tokens = self.login_tokens()
        self.bearer(tokens["access"])
        self.client.post(LOGOUT_URL, {"refresh": tokens["refresh"]}, format="json")
        self.assert_error_envelope(self.client.post(LOGOUT_URL, {"refresh": tokens["refresh"]}, format="json"), 401)

    def test_refresh_rotates_and_old_refresh_is_blacklisted(self) -> None:
        tokens = self.login_tokens()
        data = self.assert_success_envelope(self.client.post(REFRESH_URL, {"refresh": tokens["refresh"]}, format="json"))["data"]
        self.assertEqual(set(data), {"access", "refresh"})
        self.assertNotEqual(data["refresh"], tokens["refresh"])
        self.assert_error_envelope(self.client.post(REFRESH_URL, {"refresh": tokens["refresh"]}, format="json"), 401)
        self.assert_success_envelope(self.client.post(REFRESH_URL, {"refresh": data["refresh"]}, format="json"))

    def test_new_access_token_works_after_refresh(self) -> None:
        tokens = self.login_tokens()
        data = self.client.post(REFRESH_URL, {"refresh": tokens["refresh"]}, format="json").json()["data"]
        self.bearer(data["access"])
        self.assert_success_envelope(self.client.get(ME_URL))

    def test_access_token_cannot_be_used_as_refresh(self) -> None:
        tokens = self.login_tokens()
        self.assert_error_envelope(self.client.post(REFRESH_URL, {"refresh": tokens["access"]}, format="json"), 401)

    def test_refresh_for_deactivated_user_is_rejected(self) -> None:
        user = self.create_user()
        tokens = self.login_tokens(user)
        user.is_active = False
        user.save()
        self.assertEqual(self.client.post(REFRESH_URL, {"refresh": tokens["refresh"]}, format="json").status_code, 401)

    def test_refresh_garbage_and_missing_are_rejected(self) -> None:
        self.assert_error_envelope(self.client.post(REFRESH_URL, {"refresh": "garbage"}, format="json"), 401)
        self.assert_error_envelope(self.client.post(REFRESH_URL, {}, format="json"), 400)


class UserModelTests(AuthApiTestCase):
    def test_email_is_unique_at_database_level(self) -> None:
        self.create_user(email="dup@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.create_user(email="dup@example.com", name="X", password=TEST_PASSWORD)

    def test_create_user_normalises_email_and_hashes_password(self) -> None:
        user = get_user_model().objects.create_user(email="  MiXed@Example.COM ", name="X", password=TEST_PASSWORD)
        self.assertEqual(user.email, "mixed@example.com")
        self.assertNotEqual(user.password, TEST_PASSWORD)
        self.assertEqual(str(user), "mixed@example.com")

    def test_registration_race_on_duplicate_email_is_409_not_500(self) -> None:
        with patch("tracker_apps.authentication.models.user.User.email_exists", return_value=False):
            self.create_user(email="new.user@example.com")
            response = self.client.post(REGISTER_URL, self.register_payload(), format="json")
        self.assert_error_envelope(response, 409)
