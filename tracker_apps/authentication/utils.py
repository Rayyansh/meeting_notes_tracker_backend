from tracker_apps.authentication.models.user import User
from tracker_apps.common.utils import Utils

USER_RESPONSE_COLUMNS: dict[str, str] = {
    "user_id": "userId",
    "email": "email",
    "name": "name",
    "created_at": "createdAt",
}


class AuthUtils:
    @staticmethod
    def user_response(user: User) -> dict:
        row = {column: getattr(user, column) for column in USER_RESPONSE_COLUMNS}
        return Utils.map_columns(row, USER_RESPONSE_COLUMNS)
