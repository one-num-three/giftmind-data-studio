"""Common Pydantic conventions for GiftMind API contracts."""

import re

from pydantic import BaseModel, ConfigDict


def to_camel(value: str) -> str:
    """Convert a Python field name to the public JSON field name."""
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class APIModel(BaseModel):
    """Base model accepting Python and JSON-style field names."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


def normalize_text(value: str) -> str:
    """Trim and collapse whitespace in required human-entered text."""
    return re.sub(r"\s+", " ", value.strip())
