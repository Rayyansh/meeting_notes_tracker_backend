from math import ceil
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.db.models import QuerySet

from tracker.constants import Constants
from tracker_apps.common.exceptions.validation_errors import ValidationErrors

PAGE_PARAM = "page_num"
NON_FIELD = "non_field"


class Utils:
    @staticmethod
    def success_response_data(message: str, data: list | dict | None = None) -> dict:
        return {"status": True, "message": message, "data": data}

    @staticmethod
    def error_response_data(message: str, error: list) -> dict:
        return {"status": False, "message": message, "error": error}

    @staticmethod
    def map_columns(row: dict, mapping: dict[str, str]) -> dict:
        """Rename db columns to the camelCase response keys; unmapped columns are not exposed."""
        return {response_key: row[column] for column, response_key in mapping.items() if column in row}

    @staticmethod
    def flatten_errors(errors: object, prefix: str = "") -> list[dict]:
        """Turn DRF's nested serializer errors into [{"field", "message"}]."""
        if isinstance(errors, dict):
            flat: list[dict] = []
            for key, value in errors.items():
                field = f"{prefix}.{key}" if prefix else str(key)
                flat.extend(Utils.flatten_errors(value, field))
            return flat
        if isinstance(errors, (list, tuple)):
            if errors and all(isinstance(item, str) for item in errors):
                return [{"field": prefix or NON_FIELD, "message": str(item)} for item in errors]
            flat = []
            for index, item in enumerate(errors):
                field = f"{prefix}.{index}" if prefix else str(index)
                flat.extend(Utils.flatten_errors(item, field))
            return flat
        return [{"field": prefix or NON_FIELD, "message": str(errors)}]

    @staticmethod
    def paginate(queryset: QuerySet, page_num: int, limit: int) -> tuple[list, int]:
        """Return (rows of the page, total_page). An empty queryset is one empty page, never an error."""
        total_page = max(1, ceil(queryset.count() / limit))
        if page_num > total_page:
            raise ValidationErrors([{"field": PAGE_PARAM, "message": Constants.page_num_exceeded}])
        start = (page_num - 1) * limit
        return list(queryset[start : start + limit]), total_page

    @staticmethod
    def build_page_url(present_url: str, page_num: int) -> str:
        parts = urlsplit(present_url)
        query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != PAGE_PARAM]
        query.append((PAGE_PARAM, str(page_num)))
        return urlunsplit(parts._replace(query=urlencode(query)))

    @staticmethod
    def add_page_parameter(final_data: list, page_num: int, total_page: int, present_url: str) -> dict:
        to_return: dict = {"data": final_data, "presentPage": page_num, "totalPage": total_page}
        if page_num < total_page:
            to_return["nextPageUrl"] = Utils.build_page_url(present_url, page_num + 1)
        if page_num > 1:
            to_return["previousPageUrl"] = Utils.build_page_url(present_url, page_num - 1)
        return to_return
