from dataclasses import dataclass, field


@dataclass
class Register:
    email: str
    name: str
    password: str = field(repr=False)
