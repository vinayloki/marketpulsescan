# ADR-003: Bhavcopy as Primary OHLCV Source

**Status:** Accepted
**Date:** 2026-07-13
**Context:** The legacy pipeline uses yfinance as the primary OHLCV source and nse-archives as a fallback. yfinance scrapes Yahoo Finance, which is in a ToS-grey area.

## Decision

**Promote NSE bhavcopy (via `nse-archives` package) to the primary OHLCV source**, with yfinance as fallback.

## Rationale

1. **Official source** — Bhavcopy is the official end-of-day data published by NSE. It's public data intended for download.
2. **Terms of service** — removes the ToS-grey dependency from the critical path.
3. **Data quality** — bhavcopy is the canonical source; yfinance derives from it (with possible delays/adjustments).
4. **Provider abstraction exists** — the `DataProvider` base class pattern already handles fallback chains; this is a configuration change, not an architectural one.

## Implementation

- `ingestion/providers/` capability flags: `nse_archives` declared as `ohlcv_primary`
- Fallback chain: `nse_archives` → `yfinance` → error
- yfinance remains useful for: fundamentals (`.info`, `.financials`), historical data beyond bhavcopy range

## Consequences

- `nse-archives` package must be reliably installable (the `requirements.txt` corruption is fixed in Sprint 0)
- NSE website availability becomes a dependency; mitigated by yfinance fallback and `actions/cache`
- Corporate actions (splits, bonuses) need explicit handling with bhavcopy (yfinance auto-adjusts)

## Related

- [01-architecture-review.md](../planning/01-architecture-review.md) (§data sources)
- [04-target-architecture.md](../planning/04-target-architecture.md) (§data sources table)
