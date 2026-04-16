"""Unit tests for ingestion/processing behavior."""

from processing.entity_extraction import extract_entities
from processing.event_builder import build_event
from processing.noise_filter import is_noise


def test_extract_entities_hit_and_miss():
    text = "Nvidia announced a new AI feature for U.S. users."
    entities = extract_entities(text)

    assert "NVDA" in entities["companies"]
    assert "US" in entities["countries"]
    assert entities["commodities"] == []


def test_build_event_confidence_gate_blocks_low_signal():
    entities = {
        "companies": [],
        "commodities": [],
        "countries": [],
        "technologies": [],
    }
    result = build_event(
        headline="Opinion: market outlook",
        raw_text="A short note with no concrete impacts.",
        published_at="2026-01-01T00:00:00Z",
        source="unit-test",
        entities=entities,
    )
    assert result is None


def test_noise_filter_known_phrases():
    assert is_noise("Analyst said shares rose after earnings call") is True
    assert is_noise("Factory shutdown causes supply shock in copper market") is False
