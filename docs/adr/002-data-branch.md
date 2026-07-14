# ADR-002: Data Branch Separation

**Status:** Accepted
**Date:** 2026-07-13
**Context:** The legacy repo commits ~25 MB of generated data (scan_results/, SQLite DB, CSVs) directly to `main`, making branch protection impossible and polluting code history.

## Decision

Separate generated data from code using an **orphan `data` branch**:

- **Code branches** (`main`, `develop`, `feat/*`) — human-reviewed, protected, no generated data
- **Data branch** (`data`) — orphan branch written by the nightly GitHub Actions bot, force-pushed weekly to cap size

## Rationale

1. **Enables branch protection** — `main` can require PR + CI green without the bot needing push access.
2. **Clean history** — code commits separate from data commits; `git log` is readable.
3. **Bounded repo size** — weekly squash of data branch; no more unbounded growth.
4. **Eliminates fragile CI** — current `git pull --rebase && stash pop` dance in daily workflow goes away.

## Implementation

- Dataset bundles published to `data` branch under `api/v1/`
- `deploy-pages.yml` composes Pages artifact from `main` (UI) + `data` (dataset)
- CI `guard` job fails PRs that add data files to code branches

## Consequences

- Data branch must be created as an orphan: `git checkout --orphan data && git rm -rf . && git commit --allow-empty`
- Deploy workflow slightly more complex (multi-checkout composition)
- Historical scan_results stay in git history (we never rewrite)

## Related

- [08-git-branching.md](../planning/08-git-branching.md)
- [03-technical-debt.md](../planning/03-technical-debt.md) (TD-2)
