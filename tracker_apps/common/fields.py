import json
from typing import Any


class UnicodeJSONEncoder(json.JSONEncoder):
    """Keeps non-ASCII text as-is in stored JSON, so substring search on names with accents works."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["ensure_ascii"] = False
        super().__init__(*args, **kwargs)
