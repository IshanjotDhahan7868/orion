"""
Entity extraction logic for raw text.

Identify companies, commodities, countries, and technologies
mentioned in raw news articles.
"""

import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"


def _load_yaml(filename: str) -> dict:
    path = CONFIG_DIR / filename
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


COMPANIES = _load_yaml("companies.yaml")
COMMODITIES = _load_yaml("commodities.yaml")
COUNTRIES = _load_yaml("countries.yaml")
TECHNOLOGIES = _load_yaml("technologies.yaml")


def _match_entities(text: str, entity_map: dict) -> list:
    text_lower = text.lower()
    matches = []

    for key, meta in entity_map.items():
        aliases = meta.get("aliases", [])
        for alias in aliases:
            if alias.lower() in text_lower:
                matches.append(key)
                break

    return matches


def extract_entities(text: str) -> dict:
    """
    Extract structured entities from raw text.
    """
    return {
        "companies": _match_entities(text, COMPANIES),
        "commodities": _match_entities(text, COMMODITIES),
        "countries": _match_entities(text, COUNTRIES),
        "technologies": _match_entities(text, TECHNOLOGIES),
    }
