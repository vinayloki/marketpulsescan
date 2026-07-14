# Migration Guide: india-swing-scanner → MarketPulseScan

**Status:** In progress (Sprint 0 — scaffold phase)
**Last updated:** 2026-07-13

## Path Mapping (Old → New)

| Legacy Path | New Path | Status |
|---|---|---|
| `config/` | `pipeline/marketpulse/config/` | Stub created |
| `data_providers/` | `pipeline/marketpulse/ingestion/providers/` | Stub created |
| `engine/indicators.py` | `pipeline/marketpulse/technical/indicators/` | Stub created |
| `engine/timeframe_resampler.py` | `pipeline/marketpulse/technical/resampler.py` | Stub created |
| `engine/scoring_engine.py` | `pipeline/marketpulse/scoring/` | Stub created |
| `engine/opportunity_model.py` | `pipeline/marketpulse/scoring/` | Stub created |
| `engine/relative_strength.py` | `pipeline/marketpulse/sector/` | Stub created |
| `engine/alert_engine.py` | `apps/web/src/plugins/` (client-side) | Future |
| `scanners/` | `pipeline/marketpulse/technical/scanners/` | Stub created |
| `database/` | `pipeline/marketpulse/db/` | Stub created |
| `ai_engine.py` | `pipeline/marketpulse/scoring/` | Stub created |
| `backtest.py` | `pipeline/marketpulse/backtest/` | Stub created |
| `performance.py` | `pipeline/marketpulse/backtest/` | Stub created |
| `risk_manager.py` | `pipeline/marketpulse/risk/` | Stub created |
| `regime_filter.py` | `pipeline/marketpulse/regime/` | Stub created |
| `prediction/` | `pipeline/marketpulse/prediction/` | Stub created |
| `prediction_engine.py` | `pipeline/marketpulse/prediction/` | Stub created |
| `news_fetcher.py` | `pipeline/marketpulse/ingestion/news.py` | Stub created |
| `scanner.py` | `pipeline/marketpulse/cli.py` (orchestrator) | Stub created |
| `export_static_api.py` | `pipeline/marketpulse/publish/` | Stub created |
| `frontend/` | `apps/web/` | Scaffolded (TS+React+Tailwind) |
| `index.html` + `app.js` | `archive/` (at parity) | Frozen |
| `app.py` (Streamlit) | `archive/` or deleted | Frozen |
| `api/` (FastAPI) | Deleted (dead code) | — |
| `*.pine` | `docs/strategies/` | Future |
| `ISME_INSTRUCTIONS.md` | `docs/strategies/` | Future |
| `scan_results/` | `data` branch → `api/v1/` | Sprint 1 |

## Migration Sequence

1. **Sprint 0** — Scaffold new structure alongside legacy; fix requirements.txt
2. **Sprint 1** — Port data providers + publish module; shadow nightly run to staging
3. **Sprint 2** — Port indicators + sector analysis
4. **Sprint 3** — Port scoring + fundamentals; 5 green shadow runs
5. **Sprint 4-5** — Build new web UI to parity+
6. **Sprint 6** — Flip production: new app at `/`, legacy at `/legacy/`

## Key Rules

- **Never overwrite working code** — legacy files stay functional until parity
- **Never rewrite git history** — old scan_results stay in history
- **One module per PR** — each migration is an isolated, testable change
- **Golden tests** — lock legacy outputs before refactoring scoring logic
