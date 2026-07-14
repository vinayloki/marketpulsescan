"""
MarketPulseScan — News Ingestion Module

Port of legacy news_fetcher.py as a typed, importable module.
Fetches RSS feeds for Indian market news (Livemint, ET, RBI).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from marketpulse.config.settings import NEWS_FEEDS, NEWS_LOOKBACK_HOURS

log = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """A single news article from an RSS feed."""

    source: str
    title: str
    link: str
    published: datetime
    summary: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "title": self.title,
            "link": self.link,
            "time": self.published.strftime("%d %b %H:%M"),
            "timestamp": self.published.timestamp(),
            "summary": self.summary,
        }


def fetch_news(
    *,
    hours_back: int = NEWS_LOOKBACK_HOURS,
    feeds: dict[str, str] | None = None,
) -> list[NewsItem]:
    """
    Fetch recent news articles from RSS feeds.

    Args:
        hours_back: Cutoff window (articles older than this are dropped).
        feeds:      {name: url} mapping. Defaults to settings.NEWS_FEEDS.

    Returns:
        List of NewsItem sorted by published descending (newest first).
        Empty list if all feeds fail.
    """
    try:
        import feedparser
    except ImportError:
        log.error("feedparser not installed — news fetch skipped")
        return []

    if feeds is None:
        feeds = NEWS_FEEDS

    cutoff = datetime.now(tz=UTC) - timedelta(hours=hours_back)
    items: list[NewsItem] = []

    for source_name, url in feeds.items():
        log.info("News: fetching %s", source_name)
        try:
            feed = feedparser.parse(url)
            added = 0

            for entry in feed.entries:
                published = _parse_published(entry)
                if published is None:
                    continue

                # Normalise to UTC for comparison
                if published.tzinfo is None:
                    published = published.replace(tzinfo=UTC)

                if published > cutoff:
                    items.append(
                        NewsItem(
                            source=source_name,
                            title=getattr(entry, "title", ""),
                            link=getattr(entry, "link", ""),
                            published=published,
                            summary=getattr(entry, "summary", "")[:500],
                        )
                    )
                    added += 1

            log.info("News: %d recent articles from %s", added, source_name)

        except Exception as exc:
            log.error("News: failed to fetch %s: %s", source_name, exc)

    items.sort(key=lambda x: x.published, reverse=True)
    log.info("News: %d total articles fetched", len(items))
    return items


def _parse_published(entry: object) -> datetime | None:
    """Extract and parse the published date from a feedparser entry."""
    parsed = getattr(entry, "published_parsed", None)
    if parsed:
        try:
            t = tuple(parsed[:6])
            return datetime(
                int(t[0]),
                int(t[1]),
                int(t[2]),
                int(t[3]),
                int(t[4]),
                int(t[5]),
                tzinfo=UTC,
            )
        except (TypeError, ValueError, IndexError):
            pass

    # Fallback: try updated_parsed
    updated = getattr(entry, "updated_parsed", None)
    if updated:
        try:
            t = tuple(updated[:6])
            return datetime(
                int(t[0]),
                int(t[1]),
                int(t[2]),
                int(t[3]),
                int(t[4]),
                int(t[5]),
                tzinfo=UTC,
            )
        except (TypeError, ValueError, IndexError):
            pass

    return None
