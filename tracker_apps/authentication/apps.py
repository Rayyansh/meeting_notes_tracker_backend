from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "tracker_apps.authentication"

    def ready(self) -> None:
        from tracker_apps.authentication import schema  # noqa: F401  (registers the OpenAPI auth scheme)
