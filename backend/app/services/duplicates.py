"""Duplicate detection for canonical gift names and aliases."""

from dataclasses import dataclass
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


def trigram_similarity(left: str, right: str) -> float:
    """Return Dice similarity for the names' overlapping, normalized trigrams."""
    left_trigrams = _trigrams(left)
    right_trigrams = _trigrams(right)
    if not left_trigrams or not right_trigrams:
        return 0.0
    return 2 * len(left_trigrams & right_trigrams) / (len(left_trigrams) + len(right_trigrams))


def _trigrams(value: str) -> set[str]:
    normalized = normalize_name(value)
    return {normalized[index:index + 3] for index in range(len(normalized) - 2)}


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
            trigram_similarity(candidate, known)
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
