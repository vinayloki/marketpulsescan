"""
Unit tests for ingestion/news.py — feedparser mocked.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from marketpulse.ingestion.news import NewsItem, _parse_published, fetch_news

# ── NewsItem tests ────────────────────────────────────────────────────────────


def test_news_item_to_dict():
    item = NewsItem(
        source="Test Source",
        title="Market Rallies",
        link="https://example.com/article",
        published=datetime(2025, 7, 13, 14, 0, tzinfo=UTC),
        summary="Summary text",
    )
    d = item.to_dict()
    assert d["source"] == "Test Source"
    assert d["title"] == "Market Rallies"
    assert d["link"] == "https://example.com/article"
    assert "time" in d
    assert "timestamp" in d
    assert d["summary"] == "Summary text"


def test_news_item_summary_is_optional():
    item = NewsItem(source="X", title="Y", link="Z", published=datetime.now(tz=UTC))
    assert item.summary == ""


# ── _parse_published ──────────────────────────────────────────────────────────


def test_parse_published_from_published_parsed():
    entry = MagicMock()
    entry.published_parsed = (2025, 7, 13, 14, 30, 0, 0, 0, 0)
    result = _parse_published(entry)
    assert result is not None
    assert result.year == 2025
    assert result.month == 7
    assert result.day == 13


def test_parse_published_falls_back_to_updated():
    entry = MagicMock()
    entry.published_parsed = None
    entry.updated_parsed = (2025, 6, 1, 10, 0, 0, 0, 0, 0)
    result = _parse_published(entry)
    assert result is not None
    assert result.month == 6


def test_parse_published_returns_none_when_no_date():
    entry = MagicMock()
    entry.published_parsed = None
    entry.updated_parsed = None
    result = _parse_published(entry)
    assert result is None


def test_parse_published_handles_malformed_tuple():
    entry = MagicMock()
    entry.published_parsed = "not-a-tuple"
    entry.updated_parsed = None
    result = _parse_published(entry)
    assert result is None


# ── fetch_news ────────────────────────────────────────────────────────────────


def _make_entry(hours_ago: float, title: str = "Test Article") -> MagicMock:
    published = datetime.now(tz=UTC) - timedelta(hours=hours_ago)
    entry = MagicMock()
    entry.published_parsed = (
        published.year,
        published.month,
        published.day,
        published.hour,
        published.minute,
        published.second,
        0,
        0,
        0,
    )
    entry.title = title
    entry.link = "https://example.com/article"
    entry.summary = "Test summary"
    return entry


def _make_feed(entries: list[MagicMock]) -> MagicMock:
    feed = MagicMock()
    feed.entries = entries
    return feed


def test_fetch_news_filters_old_articles():
    recent_entry = _make_entry(hours_ago=12, title="Recent News")
    old_entry = _make_entry(hours_ago=48, title="Old News")

    feeds = {"TestFeed": "https://example.com/rss"}

    with patch("feedparser.parse", return_value=_make_feed([recent_entry, old_entry])):
        items = fetch_news(hours_back=36, feeds=feeds)

    titles = [i.title for i in items]
    assert "Recent News" in titles
    assert "Old News" not in titles


def test_fetch_news_sorted_newest_first():
    e1 = _make_entry(hours_ago=2, title="Oldest")
    e2 = _make_entry(hours_ago=1, title="Newest")

    with patch("feedparser.parse", return_value=_make_feed([e1, e2])):
        items = fetch_news(hours_back=36, feeds={"F": "url"})

    assert items[0].title == "Newest"
    assert items[1].title == "Oldest"


def test_fetch_news_handles_feed_failure():
    """A failing feed should not crash the whole fetch."""
    with patch("feedparser.parse", side_effect=Exception("network error")):
        items = fetch_news(feeds={"Failing": "https://bad.url/rss"})
    assert items == []


def test_fetch_news_empty_when_feedparser_missing():
    with patch.dict("sys.modules", {"feedparser": None}):
        # feedparser import will fail
        items = fetch_news(feeds={"X": "url"})
    # Should return empty list, not raise
    assert isinstance(items, list)


def test_fetch_news_multiple_feeds():
    e1 = _make_entry(hours_ago=5, title="Feed A Article")
    e2 = _make_entry(hours_ago=3, title="Feed B Article")

    call_count = 0

    def mock_parse(url):
        nonlocal call_count
        call_count += 1
        return _make_feed([e1]) if "feedA" in url else _make_feed([e2])

    with patch("feedparser.parse", side_effect=mock_parse):
        items = fetch_news(
            hours_back=36,
            feeds={"Feed A": "feedA", "Feed B": "feedB"},
        )

    assert call_count == 2
    titles = [i.title for i in items]
    assert "Feed A Article" in titles
    assert "Feed B Article" in titles
