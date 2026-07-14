# MarketPulseScan

**Zero-cost Indian stock analysis platform** — nightly EOD scanning, AI-powered picks, technical & fundamental analysis for NSE/BSE stocks.

[![CI](https://github.com/vinayloki/marketpulsescan/actions/workflows/ci.yml/badge.svg)](https://github.com/vinayloki/marketpulsescan/actions/workflows/ci.yml)
[![Pages](https://github.com/vinayloki/marketpulsescan/actions/workflows/deploy-pages.yml/badge.svg)](https://vinayloki.github.io/marketpulsescan/)

## How It Works

```
GitHub Actions (nightly, 16:15 IST)
  → Python pipeline scans ~3,000 NSE/BSE stocks
  → Computes indicators, scores, and AI picks
  → Publishes JSON dataset to GitHub Pages

Browser loads static JSON → React app renders everything client-side
```

**Total hosting cost: ₹0.** No servers, no databases in production.

## Architecture

| Component | Stack | Location |
|---|---|---|
| **Pipeline** | Python 3.12, pandas, scikit-learn | [`pipeline/`](pipeline/) |
| **Web App** | TypeScript, React 19, Vite, Tailwind CSS 4 | [`apps/web/`](apps/web/) |
| **Schemas** | JSON Schema (Draft 2020-12) | [`schemas/v1/`](schemas/v1/) |
| **Data** | JSON on orphan `data` branch | `api/v1/` |

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 22+
- Git

### Pipeline (Python)

```bash
cd pipeline
pip install -e ".[dev]"

# Lint & type-check
ruff check .
mypy .

# Run tests
pytest
```

### Web App (TypeScript + React)

```bash
cd apps/web
npm install

# Start dev server
npm run dev

# Lint, type-check, and test
npm run lint
npm run typecheck
npm run test
```

### Using Fixture Data

The dev server loads fixture data from `pipeline/tests/fixtures/bundle/`. To point at production data instead:

```bash
VITE_DATA_URL=https://vinayloki.github.io/marketpulsescan/api/v1 npm run dev
```

## Project Structure

```
marketpulsescan/
├── pipeline/               Python EOD computation pipeline
│   ├── marketpulse/        Package: config, ingestion, technical,
│   │                       scoring, risk, publish, etc.
│   └── tests/              pytest: unit, integration, fixtures
├── apps/web/               TypeScript + React + Tailwind web app
│   └── src/                Components, pages, stores, API client
├── schemas/v1/             JSON Schema contracts
├── docs/                   ADRs, migration guide, strategies
├── archive/                Frozen legacy code (at parity)
└── .github/workflows/      CI, nightly scan, deploy, backtest
```

## Contributing

1. Branch from `develop`: `git checkout -b feat/my-feature develop`
2. One module per PR, tests included
3. CI must pass: lint + type-check + tests + build
4. Never commit generated data to code branches

See [MIGRATION.md](docs/MIGRATION.md) for path mappings from the legacy structure.

## License

MIT
