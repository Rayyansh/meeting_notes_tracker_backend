from dataclasses import dataclass, field


@dataclass
class Get:
    values: str = ""
    values_list: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.values_list = [value for value in self.values.split(",") if value]
