class ProviderError(Exception):
    """A provider failed in an expected way. `code` is the machine-readable analysis_error_code."""

    code: str = "AI_PROVIDER_ERROR"


class ProviderTimeout(ProviderError):
    code = "AI_TIMEOUT"


class ProviderRateLimited(ProviderError):
    code = "AI_RATE_LIMITED"


class ProviderConfigError(ProviderError):
    """The configured provider cannot be used (unknown name, missing setting). Never carries a secret."""


class InvalidAnalysisOutput(Exception):
    """Structural failure of provider output: nothing from it may be saved. `reasons` hold paths only, never content."""

    def __init__(self, reasons: list[str]) -> None:
        super().__init__("invalid analysis output")
        self.reasons = reasons
