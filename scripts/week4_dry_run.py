from processing.entity_extraction import extract_entities
from processing.noise_filter import is_noise
from processing.event_builder import build_event

# Example test articles (replace later with real ingestion output)
TEST_ARTICLES = [
    {
        "headline": "TSMC to invest $40 billion in new Arizona chip fabs",
        "text": """
        Taiwan Semiconductor Manufacturing Company said it will invest
        $40 billion to expand its semiconductor manufacturing capacity
        in Arizona, citing strong long-term demand for advanced chips.
        """,
        "published_at": "2024-04-03",
        "source": "Reuters"
    },
    {
        "headline": "Apple shares rise after analyst raises price target",
        "text": """
        Apple shares rose 3% after an analyst raised the company's price target,
        citing strong iPhone sales expectations.
        """,
        "published_at": "2024-04-04",
        "source": "CNBC"
    }
]

for article in TEST_ARTICLES:
    print("\n---")
    print("HEADLINE:", article["headline"])

    if is_noise(article["text"]):
        print("❌ FILTERED AS NOISE")
        continue

    entities = extract_entities(article["text"])
    event = build_event(
        headline=article["headline"],
        raw_text=article["text"],
        published_at=article["published_at"],
        source=article["source"],
        entities=entities
    )
    entities = extract_entities(article["text"])
    print("ENTITIES:", entities)

    if event is None:
        print("⚠️  No actionable event detected")
    else:
        print("✅ EVENT DETECTED")
        print(event)
