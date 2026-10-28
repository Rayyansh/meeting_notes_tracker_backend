class HttpErrors(Exception):
    """Base for known, client-visible failures. `errors` holds safe, human-readable strings."""

    def __init__(self, errors: list | None = None) -> None:
        super().__init__()
        self.errors = errors or []


class NotFoundErrors(HttpErrors):
    pass


class ForbiddenErrors(HttpErrors):
    pass


class ConflictErrors(HttpErrors):
    pass


class PayloadTooLargeErrors(HttpErrors):
    pass


class UnsupportedMediaErrors(HttpErrors):
    pass


class UpstreamErrors(HttpErrors):
    """A dependency (e.g. the AI provider) failed. Carries its own status, generic message and error codes."""

    def __init__(self, http_status: int, message: str, errors: list) -> None:
        super().__init__(errors)
        self.http_status = http_status
        self.message = message
