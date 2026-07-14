"""
MarketPulseScan Pipeline CLI

Usage:
    python -m marketpulse scan [--fixture] [--output-dir DIR] [--symbols SYM,SYM]
    python -m marketpulse publish --bundle-dir DIR [--validate-only]
    python -m marketpulse holiday-check [--date YYYY-MM-DD]
    python -m marketpulse export [--output-dir DIR] [--run-id ID]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from marketpulse.config.settings import OUTPUT_DIR

log = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False) -> None:
    from marketpulse.config.settings import LOG_DATEFMT, LOG_FORMAT

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATEFMT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def cmd_scan(args: argparse.Namespace) -> int:
    """Run the full market scan (Sprint 2: indicators + scoring + sectors)."""
    import json

    from marketpulse.ingestion.ohlcv import compute_returns, extract_close_series, fetch_ohlcv
    from marketpulse.ingestion.universe import UniverseSymbol, load_universe
    from marketpulse.publish import (
        BundleWriter,
        build_market_payload,
        build_universe_payload,
        validate_bundle,
    )

    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    run_id = getattr(args, "run_id", "local")

    if args.fixture:
        log.info("Scan: using fixture data (offline mode)")
        fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "bundle" / "api" / "v1"
        with (fixture_path / "universe.json").open(encoding="utf-8") as f:
            raw_universe = json.load(f)
        universe: list[UniverseSymbol] = [
            UniverseSymbol(
                **{k: v for k, v in d.items() if k in UniverseSymbol.__dataclass_fields__}
            )
            for d in raw_universe.get(
                "data", raw_universe if isinstance(raw_universe, list) else []
            )
        ]
        with (fixture_path / "market.json").open(encoding="utf-8") as f:
            fixture_market = json.load(f)
        market_records: list[dict[str, object]] = fixture_market.get("data", [])

    else:
        from marketpulse.scoring import rank_opportunities, score_stock
        from marketpulse.sector import rs_rating_from_returns, sector_ranks
        from marketpulse.technical import compute_snapshot

        universe = load_universe()
        if not universe:
            log.error("Scan: empty universe -- aborting")
            return 1

        target_symbols = args.symbols.split(",") if args.symbols else [u.symbol for u in universe]
        log.info("Scan: %d symbols", len(target_symbols))
        ohlcv_df = fetch_ohlcv(target_symbols)

        fund_map: dict[str, dict[str, object]] = {
            u.symbol: {
                "name": u.name,
                "sector": u.sector,
                "industry": u.industry,
                "mcap_cr": u.mcap_cr,
            }
            for u in universe
        }

        market_records = []
        stock_scores = []
        rs_returns: dict[str, float] = {}

        for sym in target_symbols:
            close = extract_close_series(ohlcv_df, sym)
            returns = compute_returns(close)
            last_close = float(close.iloc[-1]) if not close.empty else None

            if returns.get("12M") is not None:
                rs_returns[sym] = float(returns["12M"])  # type: ignore[arg-type]

            snap = compute_snapshot(sym, ohlcv_df) if not ohlcv_df.empty else None
            if snap is not None:
                scored = score_stock(snap, fund_map.get(sym))
                stock_scores.append(scored)
                indicators_dict: dict[str, object] = snap.to_dict()
                rec: str | None = scored.recommendation
                signals: list[str] = scored.signals
                sub_scores: dict[str, object] = {
                    k: round(v, 1) for k, v in scored.sub_scores.items()
                }
                composite: object = round(scored.score, 1)
            else:
                indicators_dict, rec, signals, sub_scores, composite = {}, None, [], {}, None

            fund = fund_map.get(sym, {})
            record: dict[str, object] = {
                "symbol": sym,
                "name": fund.get("name"),
                "sector": fund.get("sector"),
                "exchange": "NSE",
                "mcap_cr": fund.get("mcap_cr"),
                "mcap_category": None,
                "close": last_close,
                "prev_close": float(close.iloc[-2]) if len(close) >= 2 else None,
                "returns": returns,
                "score": composite,
                "sub_scores": sub_scores,
                "recommendation": rec,
                "signals": signals,
                "indicators": indicators_dict,
            }
            market_records.append(record)

        if rs_returns:
            rs_series = rs_rating_from_returns(rs_returns)
            recs_map = {s.symbol: s.recommendation for s in stock_scores}
            sym_sector = {u.symbol: u.sector for u in universe}
            sranks = sector_ranks(rs_series, sym_sector, recs_map)
            log.info("Scan: %d sectors ranked", len(sranks))

        opportunities = rank_opportunities(stock_scores)
        log.info("Scan: %d opportunities above threshold", len(opportunities))

    writer = BundleWriter(output_dir)
    writer.write_universe(build_universe_payload([u.to_dict() for u in universe], run_id))
    writer.write_market(build_market_payload(market_records, run_id))
    writer.finalise(run_id)

    errors = validate_bundle(output_dir)
    if errors:
        for e in errors:
            log.error("Validate: %s", e)
        return 1

    log.info("Scan: bundle written to %s", output_dir / "api" / "v1")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    """Validate an existing bundle."""
    from marketpulse.publish import validate_bundle

    bundle_dir = Path(args.bundle_dir)
    errors = validate_bundle(bundle_dir)
    if errors:
        for e in errors:
            log.error("Publish: %s", e)
        return 1
    log.info("Publish: bundle at %s is valid", bundle_dir)
    return 0


def cmd_holiday_check(args: argparse.Namespace) -> int:
    """Check if a date is a trading day."""
    from datetime import date

    from marketpulse.ingestion.universe import is_trading_day, last_trading_day

    check_date: date = date.fromisoformat(args.date) if args.date else date.today()
    trading = is_trading_day(check_date)
    last_td = last_trading_day(check_date)
    print(f"Date:              {check_date.isoformat()}")
    print(f"Trading day:       {'YES' if trading else 'NO'}")
    print(f"Last trading day:  {last_td.isoformat()}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Quick export alias -- runs scan with default settings."""
    args.fixture = False
    args.symbols = None
    return cmd_scan(args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="marketpulse", description="MarketPulseScan pipeline CLI")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Run market scan and write api/v1/ bundle")
    p_scan.add_argument("--fixture", action="store_true", help="Use fixture data (offline)")
    p_scan.add_argument("--output-dir", default=None)
    p_scan.add_argument("--symbols", default=None)
    p_scan.add_argument("--run-id", default="local")

    p_pub = sub.add_parser("publish", help="Validate an existing bundle")
    p_pub.add_argument("--bundle-dir", required=True)
    p_pub.add_argument("--validate-only", action="store_true")

    p_hc = sub.add_parser("holiday-check", help="Check if a date is a trading day")
    p_hc.add_argument("--date", default=None)

    p_exp = sub.add_parser("export", help="Alias for scan with defaults")
    p_exp.add_argument("--output-dir", default=None)
    p_exp.add_argument("--run-id", default="local")

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    commands = {
        "scan": cmd_scan,
        "publish": cmd_publish,
        "holiday-check": cmd_holiday_check,
        "export": cmd_export,
    }
    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except KeyboardInterrupt:
        log.info("Interrupted")
        return 130
    except Exception as exc:
        log.exception("Unexpected error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
