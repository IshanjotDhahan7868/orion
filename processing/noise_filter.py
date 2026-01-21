"""
Noise filtering for ingestion.

Filter out uninformative or irrelevant articles before processing.
"""

NOISE_KEYWORDS = [
    "earnings call",
    "quarterly earnings",
    "price target",
    "analyst said",
    "shares rose",
    "shares fell",
    "stock jumped",
    "stock dropped",
    "interview",
    "opinion",
    "op-ed",
    "market recap"
]


def is_noise(text: str) -> bool:
    """
    Return True if the article should be ignored.
    """
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in NOISE_KEYWORDS)
