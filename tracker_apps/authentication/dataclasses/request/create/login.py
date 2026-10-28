from dataclasses import dataclass, field


@dataclass
class Login:
    email: str
    password: str = field(repr=False)
