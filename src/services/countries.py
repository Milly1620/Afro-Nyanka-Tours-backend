"""Country names: tidy what admins type, and match the different ways a country is spelled."""
import unicodedata
from typing import Iterable, List

from sqlalchemy import or_, text

# The countries we run trips in, with other spellings people use for them.
# Lookups and filters match any of these; new entries are saved as the main name.
COUNTRIES = {
    "Benin": ["Bénin", "Republic of Benin"],
    "Burkina Faso": ["Burkina"],
    "Côte d'Ivoire": ["Cote d'Ivoire", "Ivory Coast", "Cote dIvoire", "Côte d’Ivoire", "Cote d’Ivoire"],
    "Ghana": ["Republic of Ghana"],
    "Togo": ["Togolese Republic", "Republic of Togo"],
}


def _key(name: str) -> str:
    """Comparison form: 'Côte  d’Ivoire' -> "cote d'ivoire"."""
    plain = unicodedata.normalize("NFKD", name.replace("’", "'"))
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return " ".join(plain.lower().split())


_MAIN_NAME = {_key(alias): main for main, aliases in COUNTRIES.items() for alias in (main, *aliases)}


def _cap(word: str) -> str:
    return "-".join(part[:1].upper() + part[1:].lower() for part in word.split("-"))


def normalise_country(name: str) -> str:
    """'  burkina   FASO ' -> 'Burkina Faso', 'ivory coast' -> "Côte d'Ivoire".

    Known countries get their main name; anything else gets a capital on every word.
    """
    words = name.split()
    if not words:
        return ""
    return _MAIN_NAME.get(_key(name)) or " ".join(_cap(w) for w in words)


def required_country(name: str) -> str:
    """normalise_country for a field that must not end up blank (raises for pydantic -> 422)."""
    tidy = normalise_country(name)
    if not tidy:
        raise ValueError("country cannot be blank")
    return tidy


def spellings(name: str) -> List[str]:
    """Every spelling to search for: the main name and its aliases for a known country, else the name as given."""
    main = normalise_country(name)
    if main in COUNTRIES:
        return [main, *COUNTRIES[main]]
    return [name.strip()] if name.strip() else []


def country_column_matches(column, name: str):
    """SQL condition for a plain country column: contains any spelling of `name`, ignoring case."""
    return or_(*(column.ilike(f"%{s}%") for s in spellings(name)))


def event_in_countries(countries: Iterable[str]):
    """SQL condition: the event lists at least one of these countries, in any known spelling (case-insensitive)."""
    wanted = sorted({s.lower() for c in countries for s in spellings(c)})
    return text(
        "EXISTS (SELECT 1 FROM json_array_elements_text(events.countries) AS c WHERE lower(c) = ANY(:wanted))"
    ).bindparams(wanted=wanted)


def country_options() -> List[dict]:
    """The countries list for dropdowns, alphabetical."""
    return [
        {"name": main, "also_known_as": COUNTRIES[main]}
        for main in sorted(COUNTRIES, key=_key)
    ]
