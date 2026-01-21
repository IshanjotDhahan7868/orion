import feedparser
import hashlib
import psycopg2
from datetime import datetime

DB_CONN = {
    'host': 'localhost',
    'dbname': 'orion',
    'user': 'postgres',
    'password': '7294'  # <--- put your postgres password here
}

RSS_FEEDS = [
    # Add more as desired!
    'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',  # WSJ Markets
    'https://www.reuters.com/rssFeed/businessNews',   # Reuters Business
    'https://finance.yahoo.com/news/rssindex',
    'https://feeds.marketwatch.com/marketwatch/topstories',
]

def get_db_conn():
    return psycopg2.connect(**DB_CONN)

def make_hash(headline, published, source):
    to_hash = f"{headline}|{published}|{source}".encode('utf-8')
    return hashlib.sha256(to_hash).hexdigest()

def fetch_and_store():
    new_count = 0
    with get_db_conn() as conn, conn.cursor() as cur:
        for feed_url in RSS_FEEDS:
            feed = feedparser.parse(feed_url)
            source = feed.feed.get('title', 'Unknown Source')
            for entry in feed.entries:
                headline = entry.title
                url = entry.link
                raw_text = entry.summary if 'summary' in entry else ''
                published = entry.published if 'published' in entry else datetime.utcnow().isoformat()
                # Try to parse published date, fallback to now
                try:
                    if 'T' in published:
                        published_dt = datetime.strptime(published[:19], "%Y-%m-%dT%H:%M:%S")
                    else:
                        published_dt = datetime.strptime(published[:19], "%a, %d %b %Y")
                except Exception:
                    published_dt = datetime.utcnow()
                hashval = make_hash(headline, published, source)
                # Deduplication: skip if hash exists
                cur.execute("SELECT 1 FROM raw_items WHERE hash=%s", (hashval,))
                if cur.fetchone():
                    continue
                # Insert
                cur.execute("""
                    INSERT INTO raw_items (timestamp, source, url, headline, raw_text, hash)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (published_dt, source, url, headline, raw_text, hashval))
                new_count += 1
                print(f"Stored: {headline[:80]}... ({source})")
        conn.commit()
    print(f"Done! {new_count} new items added.")

if __name__ == '__main__':
    fetch_and_store()
