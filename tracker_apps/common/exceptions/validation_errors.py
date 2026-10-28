class ValidationErrors(Exception):
    """Raised for client input problems. `errors` is a list of {"field", "message"} dicts."""

    def __init__(self, errors: list) -> None:
        super().__init__()
        self.errors = errors
