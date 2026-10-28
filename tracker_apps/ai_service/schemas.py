PRIORITIES = ["Low", "Medium", "High"]

MAX_DISCUSSION_POINTS = 30
MAX_DECISIONS = 30
MAX_ACTION_ITEMS = 50
MAX_RISKS = 30
MAX_QUESTIONS = 30
MAX_TEXT = 500
MAX_EVIDENCE = 1000
MAX_SUMMARY = 4000
MAX_OWNER = 100
MAX_DUE_TEXT = 100


def evidence_item_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["text", "evidence"],
        "properties": {
            "text": {"type": "string", "minLength": 1, "maxLength": MAX_TEXT},
            "evidence": {"type": "string", "minLength": 1, "maxLength": MAX_EVIDENCE},
        },
    }


ACTION_ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["description", "owner", "due_date_text", "due_date", "priority", "evidence"],
    "properties": {
        "description": {"type": "string", "minLength": 1, "maxLength": MAX_TEXT},
        "owner": {"type": ["string", "null"], "maxLength": MAX_OWNER},
        "due_date_text": {"type": ["string", "null"], "maxLength": MAX_DUE_TEXT},
        "due_date": {"type": ["string", "null"], "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        "priority": {"enum": PRIORITIES},
        "evidence": {"type": "string", "minLength": 1, "maxLength": MAX_EVIDENCE},
    },
}

ANALYSIS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "discussion_points", "decisions", "action_items", "risks", "unanswered_questions"],
    "properties": {
        "summary": {"type": "string", "minLength": 1, "maxLength": MAX_SUMMARY},
        "discussion_points": {"type": "array", "maxItems": MAX_DISCUSSION_POINTS, "items": {"type": "string", "minLength": 1, "maxLength": MAX_TEXT}},
        "decisions": {"type": "array", "maxItems": MAX_DECISIONS, "items": evidence_item_schema()},
        "action_items": {"type": "array", "maxItems": MAX_ACTION_ITEMS, "items": ACTION_ITEM_SCHEMA},
        "risks": {"type": "array", "maxItems": MAX_RISKS, "items": evidence_item_schema()},
        "unanswered_questions": {"type": "array", "maxItems": MAX_QUESTIONS, "items": evidence_item_schema()},
    },
}
