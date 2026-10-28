import nh3

ALLOWED_TAGS: set[str] = {"p", "br", "h1", "h2", "h3", "h4", "strong", "em", "ul", "ol", "li", "a", "blockquote"}
ALLOWED_ATTRIBUTES: dict[str, set[str]] = {"a": {"href"}}
ALLOWED_URL_SCHEMES: set[str] = {"http", "https", "mailto"}


class HtmlSanitizer:
    """Server-side allow-list for rich text (meeting notes, analysis summary)."""

    @staticmethod
    def clean(html: str) -> str:
        return nh3.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, url_schemes=ALLOWED_URL_SCHEMES).strip()
