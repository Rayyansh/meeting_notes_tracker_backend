from drf_spectacular.extensions import OpenApiAuthenticationExtension


class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "tracker_apps.authentication.authentication.JWTAuthentication"
    name = "bearerAuth"

    def get_security_definition(self, auto_schema: object) -> dict:
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
