"""Duplicate detection for canonical gift names and aliases."""

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.gift import Gift


_WARNING_THRESHOLD = 0.82


@dataclass(frozen=True)
class DuplicateMatch:
    gift_id: str
    canonical_name: str
    similarity: float
    exact: bool


def normalize_name(value: str) -> str:
    """Normalize user-facing names without erasing meaningful punctuation."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).strip()).casefold()


async def find_duplicates(
    session: AsyncSession, canonical_name: str, aliases: list[str], *, exclude_gift_id: str | None = None
) -> list[DuplicateMatch]:
    """Find active exact matches and high-similarity warnings for a proposed gift."""
    candidate_names = {normalize_name(canonical_name), *(normalize_name(alias) for alias in aliases)}
    query = select(Gift).where(Gift.deleted_at.is_(None))
    if exclude_gift_id:
        query = query.where(Gift.id != exclude_gift_id)
    gifts = (await session.scalars(query)).all()
    matches: list[DuplicateMatch] = []
    for gift in gifts:
        known_names = [gift.canonical_name, *gift.aliases]
        similarity = max(
            SequenceMatcher(a=candidate, b=normalize_name(known)).ratio()
            for candidate in candidate_names
            for known in known_names
        )
        exact = any(candidate == normalize_name(known) for candidate in candidate_names for known in known_names)
        if exact or similarity > _WARNING_THRESHOLD:
            matches.append(
                DuplicateMatch(
                    gift_id=gift.id,
                    canonical_name=gift.canonical_name,
                    similarity=round(similarity, 4),
                    exact=exact,
                )
            )
    return sorted(matches, key=lambda match: (not match.exact, -match.similarity, match.canonical_name))
