# ADR-001: Static-First Architecture

**Status:** Accepted
**Date:** 2026-07-13
**Context:** MarketPulseScan is a zero-cost Indian stock analysis platform.

## Decision

The platform uses a **static-first architecture**: GitHub Actions computes, GitHub Pages serves. No servers, no databases in production, no hosting costs.

- **Compute:** GitHub Actions runs the Python pipeline nightly after NSE close (16:15 IST)
- **Serve:** GitHub Pages serves both the React UI and the JSON dataset bundle
- **Client-side dynamic features:** Screeners, watchlists, portfolio — all backed by localStorage + static JSON

## Rationale

1. **Zero hosting cost** — free tier of GitHub Actions (unlimited for public repos) + free GitHub Pages.
2. **Simplicity** — no servers to maintain, no uptime concerns, no database management.
3. **Reliability** — if the pipeline fails, yesterday's valid data stays live. The system degrades gracefully.
4. **Scalability** — GitHub CDN handles traffic; dataset is ~2-3 MB gzipped.

## Consequences

- No real-time data; nightly EOD only (acceptable for swing/position trading timeframes).
- No user accounts or server-side state; all user data lives in the browser.
- Features like alerts require client-side evaluation on page load (browser notifications).
- Premium features must be gated client-side (license key flag) — no server-side enforcement.

## Related

- [04-target-architecture.md](../planning/04-target-architecture.md)
