import re
from pathlib import PurePosixPath, PureWindowsPath

from django.core.files.uploadedfile import UploadedFile

from tracker.config import Configurations
from tracker.constants import Constants
from tracker_apps.common.exceptions.http_errors import PayloadTooLargeErrors, UnsupportedMediaErrors
from tracker_apps.common.exceptions.validation_errors import ValidationErrors

UNSAFE_NAME_CHARS = re.compile(r"[^\w .()\-]", flags=re.UNICODE)
TEXT_FIELD = "transcript"
FILE_FIELD = "transcript_file"


class TranscriptValidator:
    """The single place a transcript is checked, whether it was pasted or uploaded."""

    @staticmethod
    def normalise_newlines(text: str) -> str:
        return text.replace("\r\n", "\n").replace("\r", "\n")

    @staticmethod
    def validate_text(text: str, field: str = TEXT_FIELD) -> str:
        cleaned = TranscriptValidator.normalise_newlines(text).strip()
        if not cleaned:
            message = Constants.transcript_file_empty if field == FILE_FIELD else Constants.transcript_required
            raise ValidationErrors([{"field": field, "message": message}])
        if "\x00" in cleaned:
            raise ValidationErrors([{"field": field, "message": Constants.transcript_nul}])
        if len(cleaned) > Configurations.upload_max_bytes:
            raise ValidationErrors([{"field": field, "message": Constants.transcript_too_long}])
        return cleaned

    @staticmethod
    def from_upload(upload: UploadedFile) -> tuple[str, str]:
        """Return (transcript text, sanitised display name). The client content type is never consulted."""
        name = upload.name or ""
        if not name.lower().endswith(Constants.transcript_file_extension):
            raise UnsupportedMediaErrors([Constants.transcript_file_type])
        limit = Configurations.upload_max_bytes
        if upload.size is not None and upload.size > limit:
            raise PayloadTooLargeErrors([Constants.transcript_file_too_large])
        raw = upload.read(limit + 1)
        if len(raw) > limit:
            raise PayloadTooLargeErrors([Constants.transcript_file_too_large])
        text = TranscriptValidator.decode(raw)
        return TranscriptValidator.validate_text(text, FILE_FIELD), TranscriptValidator.display_name(name)

    @staticmethod
    def decode(raw: bytes) -> str:
        if b"\x00" in raw:
            raise UnsupportedMediaErrors([Constants.transcript_file_not_text])
        try:
            return raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise UnsupportedMediaErrors([Constants.transcript_file_not_text])

    @staticmethod
    def display_name(client_name: str) -> str:
        """A label for the UI only: base name, no path, no control characters. Never used as a file path."""
        base = PureWindowsPath(PurePosixPath(client_name).name).name
        safe = UNSAFE_NAME_CHARS.sub("_", base).strip(" .") if base else ""
        limit = Constants.transcript_file_name_max_length
        extension = Constants.transcript_file_extension
        if not safe or safe.lower() == extension[1:]:
            return Constants.transcript_file_default_name
        if not safe.lower().endswith(extension):
            safe += extension
        return safe if len(safe) <= limit else safe[: limit - len(extension)] + extension
