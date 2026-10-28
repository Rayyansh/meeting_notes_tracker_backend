class TokenErrors(Exception):
    def __init__(self, errors: list) -> None:
        super().__init__()
        self.errors = errors
