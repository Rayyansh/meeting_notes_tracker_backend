from dataclasses import dataclass


@dataclass
class Search:
    key: str
    page_num: int
    limit: int
