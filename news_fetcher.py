import feedparser
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import logging
import sys

# ─── Configuration ──────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / "scan_results"
OUTPUT_DIR.mkdir(exist_ok=True)

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUTPUT_DIR / "news_fetcher.log", mode="w", encoding="utf-8")
    ]
)
log = logging.getLogger("news_fetcher")

# 1. Define free sources (RSS Feeds for India)
FEEDS = {
    "Livemint Markets": "https://www.livemint.com/rss/markets",
    "Economic Times Stocks": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "RBI Press Releases": "https://rbi.org.in/Scripts/RSS.aspx"
    # NSE Announcements feed often blocked by bot protections unless headers are heavily faked, omitting for stability
}

def fetch_daily_news():
    log.info("📡 Starting Daily News Retrieval...")
    daily_summary = []
    
    # Set the cutoff for "once per day" (last 24 hours) + 12h buffer since feeds can be slow
    cutoff = datetime.now() - timedelta(hours=36)

    for source_name, url in FEEDS.items():
        log.info(f"   📥 Fetching {source_name}...")
        try:
            feed = feedparser.parse(url)
            added = 0
            
            for entry in feed.entries:
                # Parse published date (handling different formats)
                try:
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])
                    else:
                        continue
                except Exception:
                    continue

                if published > cutoff:
                    daily_summary.append({
                        "source": source_name,
                        "title": entry.title,
                        "link": entry.link,
                        "time": published.strftime("%d %b %H:%M"),
                        "timestamp": published.timestamp()
                    })
                    added += 1
            log.info(f"      ✅ Found {added} recent articles.")
        except Exception as e:
            log.error(f"      ❌ Failed to fetch {source_name}: {e}")
            
    # Sort by newest first
    daily_summary.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # 2. Save as JSON (to be read by your website)
    output_path = OUTPUT_DIR / "daily_news.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(daily_summary, f, indent=4, ensure_ascii=False)
        
    log.info(f"🎉 Update complete. Total {len(daily_summary)} news items saved to daily_news.json.")

if __name__ == "__main__":
    fetch_daily_news()
