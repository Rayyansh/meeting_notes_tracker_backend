from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse

from tracker.config import Configurations
from tracker.constants import Constants


class SwaggerPage:
    @staticmethod
    def response(description: str = "Success", response: object = None) -> dict:
        return {200: OpenApiResponse(description=description, response=response)}

    @staticmethod
    def get_all_parameters(
        sort_fields: tuple[str, ...] = (), default_sort_by: str = "", default_sort_order: str = "asc"
    ) -> list[OpenApiParameter]:
        query = OpenApiParameter.QUERY
        return [
            OpenApiParameter("values", OpenApiTypes.STR, query, False, "Comma separated columns to return"),
            OpenApiParameter("page_num", OpenApiTypes.INT, query, False, "Page number", default=1),
            OpenApiParameter("limit", OpenApiTypes.INT, query, False, f"Rows per page (max {Configurations.max_page_size})", default=Configurations.pagination_count),
            OpenApiParameter("sort_by", OpenApiTypes.STR, query, False, "Field to sort by", enum=list(sort_fields) or None, default=default_sort_by or None),
            OpenApiParameter("sort_order", OpenApiTypes.STR, query, False, "Sort direction", enum=["asc", "desc"], default=default_sort_order),
            OpenApiParameter("search_key", OpenApiTypes.STR, query, False, "Free-text search"),
            OpenApiParameter("from_date", OpenApiTypes.DATE, query, False, f"Filter from date ({Constants.iso_date_format})"),
            OpenApiParameter("to_date", OpenApiTypes.DATE, query, False, f"Filter to date ({Constants.iso_date_format})"),
        ]

    @staticmethod
    def get_parameters() -> list[OpenApiParameter]:
        return [OpenApiParameter("values", OpenApiTypes.STR, OpenApiParameter.QUERY, False, "Comma separated columns to return")]

    @staticmethod
    def search_parameters(key_description: str) -> list[OpenApiParameter]:
        return [OpenApiParameter("key", OpenApiTypes.STR, OpenApiParameter.QUERY, True, key_description)]
