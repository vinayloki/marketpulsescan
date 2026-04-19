"""
MarketPulse India — Scoring Engine

Fuses outputs from all scanners into a single ranked opportunity list.

Scoring rules:
    - Each scanner contributes up to its MAX_SCORE points
    - Multi-signal bonus: 2 signals → +5 pts, 3 signals → +10 pts
    - Combined score capped at 100
    - Only stocks with score >= MIN_SCORE_THRESHOLD appear in output
    - Top MAX_OPPORTUNITIES stocks are kept (ranked by score desc)
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from config.settings import (
    MAX_OPPORTUNITIES,
    MIN_SCORE_THRESHOLD,
    MULTI_SIGNAL_BONUS,
    OUTPUT_DIR,
)
from config.sector_map import normalize_sector
from engine.opportunity_model import Opportunity, ScanResult

log = logging.getLogger("marketpulse.engine")


class ScoringEngine:
    """
    Fuses scanner results → ranked Opportunity list → opportunities.json
    """

    def fuse(
        self,
        scanner_results: dict[str, dict[str, ScanResult]],
        fundamentals: dict[str, dict],
    ) -> list[Opportunity]:
        """
        Merge all scanner outputs into a single ranked list.

        Args:
            scanner_results: {scanner_name: {ticker: ScanResult}}
            fundamentals:    {ticker: fundamental_dict}

        Returns:
            List of Opportunity objects, sorted by score descending.
        """
        log.info("⚙️  Fusing scanner results...")

        # ── Aggregate per-ticker across all scanners ──────────────────
        ticker_aggregates: dict[str, dict] = {}

        for scanner_name, ticker_map in scanner_results.items():
            for ticker, result in ticker_map.items():
                if not result.triggered:
                    continue

                if ticker not in ticker_aggregates:
                    ticker_aggregates[ticker] = {
                        "score":      0,
                        "signals":    [],
                        "indicators": {},
                        "scanners":   [],
                    }

                agg = ticker_aggregates[ticker]
                agg["score"]      += result.score
                agg["signals"]    += result.signals
                agg["scanners"].append(scanner_name)
                # Merge indicators (later scanners overwrite shared keys)
                agg["indicators"].update(result.indicators)

        # ── Apply multi-signal bonus ──────────────────────────────────
        for ticker, agg in ticker_aggregates.items():
            n_scanners = len(set(agg["scanners"]))
            bonus = MULTI_SIGNAL_BONUS.get(n_scanners, 0)
            agg["score"] = min(100, agg["score"] + bonus)

        # ── Filter below threshold ────────────────────────────────────
        qualified = {
            t: agg for t, agg in ticker_aggregates.items()
            if agg["score"] >= MIN_SCORE_THRESHOLD
        }

        # ── Sort and rank ─────────────────────────────────────────────
        ranked = sorted(
            qualified.items(),
            key=lambda x: x[1]["score"],
            reverse=True,
        )[:MAX_OPPORTUNITIES]

        # ── Build Opportunity objects ─────────────────────────────────
        opportunities: list[Opportunity] = []
        for rank, (ticker, agg) in enumerate(ranked, start=1):
            fund = fundamentals.get(ticker, {})

            # Clean fundamental dict for output
            fund_clean = {
                "name":    fund.get("name") or ticker,
                "sector":  normalize_sector(fund.get("sector")),
                "ind":     fund.get("ind"),
                "mcap_cr": fund.get("mcap"),
                "pe":      fund.get("pe"),
                "eps":     fund.get("eps"),
                "52h":     fund.get("52h"),
                "52l":     fund.get("52l"),
                "bv":      fund.get("bv"),
                "dy":      fund.get("dy"),
            }

            opp = Opportunity(
                ticker=ticker,
                rank=rank,
                score=agg["score"],
                signals=sorted(set(agg["signals"])),
                indicators=agg["indicators"],
                fundamental=fund_clean,
            )
            opportunities.append(opp)

        log.info(
            f"   ✅ {len(opportunities)} opportunities "
            f"(threshold: {MIN_SCORE_THRESHOLD}+, max: {MAX_OPPORTUNITIES})"
        )
        return opportunities

    def save(self, opportunities: list[Opportunity]) -> Path:
        """
        Write opportunities.json to scan_results/.

        Schema:
        {
            "generated":         "09 Apr 2026",
            "engine_version":    "2.0",
            "total_opportunities": 42,
            "opportunities":     [ {Opportunity.to_dict()}, ... ]
        }
        """
        output = {
            "generated":           datetime.now().strftime("%d %b %Y"),
            "generated_ts":        datetime.now().strftime("%Y-%m-%d_%H%M"),
            "engine_version":      "2.0",
            "total_opportunities": len(opportunities),
            "opportunities":       [opp.to_dict() for opp in opportunities],
        }

        path = OUTPUT_DIR / "opportunities.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)

        log.info(f"   📄 opportunities.json saved ({len(opportunities)} entries)")
        return path
