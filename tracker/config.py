from decouple import Csv, config


class Configurations:
    secret_key = config("SECRET_KEY")
    debug = config("DEBUG", default=False, cast=bool)
    allowed_hosts = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
    cors_allowed_origins = config("CORS_ALLOWED_ORIGINS", default="http://localhost:5173", cast=Csv())

    db_path = config("DB_PATH", default="db.sqlite3")
    db_timeout_seconds = config("DB_TIMEOUT_SECONDS", default=20, cast=int)

    access_token_minutes = config("ACCESS_TOKEN_MINUTES", default=15, cast=int)
    refresh_token_days = config("REFRESH_TOKEN_DAYS", default=7, cast=int)
    login_throttle_rate = config("LOGIN_THROTTLE_RATE", default="10/min")
    register_throttle_rate = config("REGISTER_THROTTLE_RATE", default="5/min")

    pagination_count = config("PAGINATION_COUNT", default=10, cast=int)
    max_page_size = config("MAX_PAGE_SIZE", default=100, cast=int)

    upload_max_bytes = config("UPLOAD_MAX_BYTES", default=1048576, cast=int)

    ai_provider = config("AI_PROVIDER", default="mock")
    ai_timeout_seconds = config("AI_TIMEOUT_SECONDS", default=30, cast=int)
    ai_max_transcript_chars = config("AI_MAX_TRANSCRIPT_CHARS", default=100000, cast=int)
    gemini_api_key = config("GEMINI_API_KEY", default="")
    gemini_model = config("GEMINI_MODEL", default="")

    log_level = config("LOG_LEVEL", default="INFO")
    secure_ssl_redirect = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
