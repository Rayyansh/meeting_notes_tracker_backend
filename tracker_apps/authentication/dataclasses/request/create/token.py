from dataclasses import dataclass, field


@dataclass
class TokenRefresh:
    refresh: str = field(repr=False)
