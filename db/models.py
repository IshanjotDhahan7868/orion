"""Database model notes for ORION.

The project currently uses a lightweight SQLite state store in `db/store.py`
to persist private-user intelligence state:

- ontology_entities / ontology_relationships
- signals_cache / events_cache
- watchlists
- portfolio_snapshots
- analyst_briefs

This file remains as the conceptual model reference until a heavier ORM layer
is justified.
"""
