from dataclasses import dataclass, field
from datetime import date


@dataclass
class GetAll:
    page_num: int
    limit: int
    sort_by: str
    sort_order: str
    search_key: str = ""
    values: str = ""
    from_date: date | None = None
    to_date: date | None = None
    values_list: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.values_list = [value for value in self.values.split(",") if value]

    @property
    def ordering(self) -> str:
        return f"{'-' if self.sort_order == 'desc' else ''}{self.sort_by}"
