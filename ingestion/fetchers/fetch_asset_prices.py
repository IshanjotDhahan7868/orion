import yfinance as yf
import psycopg2
from datetime import datetime
import yaml

DB_CONN = {
    'host': 'localhost',
    'dbname': 'orion',
    'user': 'postgres',
    'password': '7294'
}

# List of tickers you want to fetch prices for:
TICKERS = get_all_tickers_from_graph('config/graph.yaml')



def get_db_conn():
    return psycopg2.connect(**DB_CONN)


def get_all_tickers_from_graph(graph_path):
    with open(graph_path, 'r') as f:
        graph = yaml.safe_load(f)

    tickers = set()
    for node in graph['nodes']:
        assets = node.get('assets', {})
        for key in ['equities', 'etfs', 'commodities']:
            for ticker in assets.get(key, []):
                # Only grab strings (ignore None/empty)
                if isinstance(ticker, str) and ticker:
                    tickers.add(ticker)
    return sorted(list(tickers))


def fetch_and_store_prices():
    with get_db_conn() as conn, conn.cursor() as cur:
        for ticker in TICKERS:
            print(f"Fetching {ticker}...")
            try:
                data = yf.download(ticker, period="2y", interval="1d", progress=False)
                for date, row in data.iterrows():
                    price_date = date.date()
                    close = float(row['Close'].iloc[0]) if hasattr(row['Close'], 'iloc') else float(row['Close'])
                    volume = int(row['Volume'].iloc[0]) if hasattr(row['Volume'], 'iloc') else int(row['Volume'])
                    cur.execute("""
                        INSERT INTO asset_prices (ticker, price_date, close, volume)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (ticker, price_date) DO NOTHING
                    """, (ticker, price_date, close, volume))
                print(f"Stored price history for {ticker}")
            except Exception as e:
                print(f"Failed to fetch/store {ticker}: {e}")
        conn.commit()
    print("Done fetching price history.")

if __name__ == '__main__':
    fetch_and_store_prices()
