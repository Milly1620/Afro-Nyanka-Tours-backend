"""Tidy country names typed by admins, and match events by country."""
import unicodedata
from typing import Iterable, List

from sqlalchemy import text

# Spellings that word-by-word capitalising would get wrong, keyed by _key().
_KNOWN = {
    "cote d'ivoire": "Côte d'Ivoire",
    "ivory coast": "Côte d'Ivoire",
}


def _key(name: str) -> str:
    """Lowercase, accents dropped: 'Côte d’Ivoire' -> "cote d'ivoire"."""
    plain = unicodedata.normalize("NFKD", name.replace("’", "'"))
    return "".join(c for c in plain if not unicodedata.combining(c)).lower()


def _cap(word: str) -> str:
    return "-".join(part[:1].upper() + part[1:].lower() for part in word.split("-"))


def normalise_country(name: str) -> str:
    """'  burkina   FASO ' -> 'Burkina Faso'. Every word gets a capital first letter."""
    words = name.split()
    if not words:
        return ""
    joined = " ".join(words)
    return _KNOWN.get(_key(joined)) or " ".join(_cap(w) for w in words)


def required_country(name: str) -> str:
    """normalise_country for a field that must not end up blank (raises for pydantic -> 422)."""
    tidy = normalise_country(name)
    if not tidy:
        raise ValueError("country cannot be blank")
    return tidy


def event_in_countries(countries: Iterable[str]):
    """SQL condition: the event lists at least one of these countries (case-insensitive)."""
    wanted: List[str] = [normalise_country(c).lower() for c in countries if c.strip()]
    return text(
        "EXISTS (SELECT 1 FROM json_array_elements_text(events.countries) AS c WHERE lower(c) = ANY(:wanted))"
    ).bindparams(wanted=wanted)
