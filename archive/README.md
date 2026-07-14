# Archive

This directory holds frozen legacy code that has been superseded by the new architecture but is preserved per the **"never overwrite working code"** principle.

## What goes here

- `index.html` + `app.js` — the original vanilla JS dashboard (moved here when new web app reaches feature parity)
- `app.py` — Streamlit local dashboard (moved here or deleted)
- `api/` — unused FastAPI routes

## When files move here

Files are only moved to `archive/` when:
1. The new system has **verified feature parity** on staging
2. The move is done in a **single reviewed PR**
3. The old URL remains accessible at `/legacy/` for one release cycle

## Status

- [ ] Awaiting Sprint 6 (Production Cutover)
