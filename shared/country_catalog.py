"""Canonical monitored-country catalog shared across backend layers."""

from __future__ import annotations

from typing import Final, TypedDict


class CountryMetadata(TypedDict):
    """Repository-facing metadata for one monitored country."""

    code: str
    name: str
    region: str
    income_level: str


MONITORED_COUNTRIES: Final[tuple[CountryMetadata, ...]] = (
    {"code": "BR", "name": "Brazil", "region": "Latin America & Caribbean", "income_level": "Upper middle income"},
    {"code": "CA", "name": "Canada", "region": "North America", "income_level": "High income"},
    {"code": "GB", "name": "United Kingdom", "region": "Europe & Central Asia", "income_level": "High income"},
    {"code": "US", "name": "United States", "region": "North America", "income_level": "High income"},
    {"code": "BS", "name": "Bahamas, The", "region": "Latin America & Caribbean", "income_level": "High income"},
    {"code": "CO", "name": "Colombia", "region": "Latin America & Caribbean", "income_level": "Upper middle income"},
    {"code": "SV", "name": "El Salvador", "region": "Latin America & Caribbean", "income_level": "Upper middle income"},
    {"code": "GE", "name": "Georgia", "region": "Europe & Central Asia", "income_level": "Upper middle income"},
    {"code": "HU", "name": "Hungary", "region": "Europe & Central Asia", "income_level": "High income"},
    {"code": "MY", "name": "Malaysia", "region": "East Asia & Pacific", "income_level": "Upper middle income"},
    {"code": "NZ", "name": "New Zealand", "region": "East Asia & Pacific", "income_level": "High income"},
    {"code": "RU", "name": "Russian Federation", "region": "Europe & Central Asia", "income_level": "High income"},
    {"code": "SG", "name": "Singapore", "region": "East Asia & Pacific", "income_level": "High income"},
    {"code": "ES", "name": "Spain", "region": "Europe & Central Asia", "income_level": "High income"},
    {"code": "CH", "name": "Switzerland", "region": "Europe & Central Asia", "income_level": "High income"},
    {"code": "TR", "name": "Turkiye", "region": "Europe & Central Asia", "income_level": "Upper middle income"},
    {"code": "UY", "name": "Uruguay", "region": "Latin America & Caribbean", "income_level": "High income"},
)

MONITORED_COUNTRY_CATALOG: Final[dict[str, CountryMetadata]] = {
    country["code"]: dict(country)
    for country in MONITORED_COUNTRIES
}

MONITORED_COUNTRY_CODES: Final[tuple[str, ...]] = tuple(
    country["code"]
    for country in MONITORED_COUNTRIES
)

MONITORED_COUNTRY_CODES_LOWER: Final[tuple[str, ...]] = tuple(
    country_code.lower()
    for country_code in MONITORED_COUNTRY_CODES
)