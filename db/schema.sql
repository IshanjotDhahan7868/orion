-- News intake (raw)
CREATE TABLE raw_items (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    source VARCHAR(128) NOT NULL,
    url TEXT NOT NULL,
    headline TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    hash CHAR(64) NOT NULL,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT now()
);
CREATE UNIQUE INDEX idx_raw_items_hash ON raw_items(hash);

-- Events (classified/structured)
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    raw_item_id INTEGER REFERENCES raw_items(id) ON DELETE CASCADE,
    event_time TIMESTAMP NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    confidence REAL,
    affected_nodes TEXT[],
    summary TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);

-- Graph nodes/edges (import from YAML)
CREATE TABLE graph_nodes (
    id VARCHAR(64) PRIMARY KEY,
    theme VARCHAR(64),
    type VARCHAR(64),
    what_is_this TEXT,
    what_affects_it TEXT[],
    assets JSONB
);
CREATE TABLE graph_edges (
    id SERIAL PRIMARY KEY,
    from_node VARCHAR(64) REFERENCES graph_nodes(id),
    to_node VARCHAR(64) REFERENCES graph_nodes(id),
    weight REAL,
    lag VARCHAR(16)
);

-- Tickers/assets
CREATE TABLE tickers (
    ticker VARCHAR(16) PRIMARY KEY,
    name TEXT,
    asset_type VARCHAR(32),
    region VARCHAR(32),
    node_ids TEXT[]
);

-- Asset prices (history)
CREATE TABLE asset_prices (
    ticker VARCHAR(16),
    price_date DATE,
    close REAL,
    volume BIGINT,
    PRIMARY KEY (ticker, price_date)
);
