from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

TEST_PASSWORD = "Str0ng-Passw0rd!"
FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class ApiTestCase(APITestCase):
    """Shared base: fast hasher, clean throttle cache, user factory and envelope assertions."""

    def setUp(self) -> None:
        super().setUp()
        cache.clear()

    @staticmethod
    def create_user(email: str = "user@example.com", name: str = "Test User", password: str = TEST_PASSWORD):
        return get_user_model().objects.create_user(email=email, name=name, password=password)

    def authenticate(self, user) -> None:
        self.client.force_authenticate(user)

    def assert_error_envelope(self, response, http_status: int) -> dict:
        self.assertEqual(response.status_code, http_status)
        body = response.json()
        self.assertIs(body["status"], False)
        self.assertIsInstance(body["message"], str)
        self.assertIsInstance(body["error"], list)
        return body

    def assert_success_envelope(self, response, http_status: int = 200) -> dict:
        self.assertEqual(response.status_code, http_status)
        body = response.json()
        self.assertIs(body["status"], True)
        self.assertIn("message", body)
        self.assertIn("data", body)
        return body
