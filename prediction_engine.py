"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  MarketPulse India — Prediction Engine                                       ║
║                                                                              ║
║  Orchestrates the full prediction + accuracy pipeline:                       ║
║    1. Load OHLCV parquet cache (reused from backtest.py)                    ║
║    2. Build weekly feature matrix (vectorized, 2100+ stocks)                ║
║    3. Check RF retraining triggers → retrain if needed                       ║
║    4. Generate next-week BUY/SELL/HOLD predictions                          ║
║    5. Run walk-forward prediction accuracy backtest                          ║
║    6. Compute metrics + benchmarks                                           ║
║    7. Write predictions.json + prediction_accuracy.json                      ║
║                                                                              ║
║  Fallback: if ANY stage fails, falls back to ai_picks.json scores           ║
║  and marks predictions with method='fallback_ai_score'.                      ║
║                                                                              ║
║  Usage:                                                                      ║
║    python prediction_engine.py                                               ║
║    python prediction_engine.py --backtest-weeks 26                          ║
║    python prediction_engine.py --force-download                              ║
║    python prediction_engine.py --no-backtest                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("prediction_engine")

# ── Paths ─────────────────────────────────────────────────────────────────────
OUTPUT_DIR           = Path("scan_results")
AI_PICKS_FILE        = OUTPUT_DIR / "ai_picks.json"
MARKET_REGIME_FILE   = OUTPUT_DIR / "market_regime.json"
PREDICTIONS_OUT      = OUTPUT_DIR / "predictions.json"
PRED_ACCURACY_OUT    = OUTPUT_DIR / "prediction_accuracy.json"

OUTPUT_DIR.mkdir(exist_ok=True)


# ── Load market regime ────────────────────────────────────────────────────────

def load_regime() -> str:
    if MARKET_REGIME_FILE.exists():
        try:
            with open(MARKET_REGIME_FILE, encoding="utf-8") as fh:
                rj = json.load(fh)
            regime = rj.get("regime", "Bull")
            log.info(f"[OK] Market regime: {regime}")
            return regime
        except Exception as exc:
            log.warning(f"[WARN] market_regime.json parse error: {exc}")
    log.info("[INFO] market_regime.json not found — defaulting to Bull")
    return "Bull"


# ── Fallback: build predictions from ai_picks.json ───────────────────────────

def fallback_from_ai_picks(regime: str) -> list[dict]:
    """
    If the prediction engine fails, build degraded predictions from ai_picks.json.
    Confidence is halved and method is flagged as 'fallback_ai_score'.
    """
    if not AI_PICKS_FILE.exists():
        log.error("[FAIL] ai_picks.json not found — cannot generate fallback predictions")
        return []
    try:
        with open(AI_PICKS_FILE, encoding="utf-8") as fh:
            ai = json.load(fh)
        picks = []
        for p in ai.get("picks", []):
            rec = p.get("recommendation", "hold")
            pred_label = {"buy": "BUY", "sell": "SELL", "hold": "HOLD"}.get(rec, "HOLD")
            original_conf = p.get("confidence", 50)
            picks.append({
                "ticker":              p.get("ticker", ""),
                "prediction":          pred_label,
                "confidence":          int(original_conf * 0.5),  # halved = low confidence
                "expected_return_pct": round(p.get("tp_pct", 4.0) if rec == "buy"
                                             else -p.get("sl_pct", 2.0) if rec == "sell"
                                             else 0.0, 2),
                "reasoning": {
                    "top_features": [],
                    "narrative":    f"Fallback from AI score (original conf: {original_conf}%)",
                },
            })
        log.info(f"[OK] Fallback: {len(picks)} picks from ai_picks.json")
        return picks
    except Exception as exc:
        log.error(f"[FAIL] Could not load ai_picks.json fallback: {exc}")
        return []


# ── Stock State Classifier (SQUEEZE / QUIET / LEADER / NEUTRAL) ───────────────

def classify_stock_state(feat_row: "pd.Series") -> tuple[str, str]:
    """
    Classify a stock into one of four states using the already-computed
    feature row from build_feature_matrix().

    Priority order: SQUEEZE > QUIET > LEADER > NEUTRAL
    (A squeezed stock that is also a leader is still SQUEEZE — the setup is
    about the coming breakout, not past outperformance.)

    Args:
        feat_row: A row from the features DataFrame with fields:
                  bb_squeeze, atr_pct, vol_contraction, vol_ratio,
                  sector_rs_pct, rsi_14, ema_aligned

    Returns:
        (state, reason) — state is one of SQUEEZE/QUIET/LEADER/NEUTRAL
    """
    bb_sq   = feat_row.get("bb_squeeze", 0)
    atr_pct = feat_row.get("atr_pct", 3.0)
    vol_con = feat_row.get("vol_contraction", 0)
    vol_rat = feat_row.get("vol_ratio", 1.0)
    rs_pct  = feat_row.get("sector_rs_pct", 0.0)
    rsi     = feat_row.get("rsi_14", 50.0)
    ema_al  = feat_row.get("ema_aligned", 0)

    # Safe-convert — features can be NaN
    def _f(v, default=0.0):
        try:
            f = float(v)
            return default if (f != f) else f  # NaN check
        except Exception:
            return default

    bb_sq   = int(_f(bb_sq))
    atr_pct = _f(atr_pct, 3.0)
    vol_con = int(_f(vol_con))
    vol_rat = _f(vol_rat, 1.0)
    rs_pct  = _f(rs_pct, 0.0)
    rsi     = _f(rsi, 50.0)
    ema_al  = int(_f(ema_al))

    # ── SQUEEZE: BB compressed + low volatility (coiled setup) ───────────────
    if bb_sq == 1 and atr_pct < 2.5:
        reason = (
            f"BB compressed (ATR {atr_pct:.1f}%) · "
            f"RSI {rsi:.0f} · Awaiting breakout"
        )
        return "SQUEEZE", reason

    # ── QUIET: Volume drying up + low ATR (accumulation/distribution) ────────
    if vol_con == 1 and atr_pct < 1.8:
        vol_desc = f"Vol ratio {vol_rat:.2f}x 20w avg"
        reason = (
            f"Low ATR {atr_pct:.1f}% · {vol_desc} · "
            f"Possible quiet accumulation"
        )
        return "QUIET", reason

    # ── LEADER: Outpacing market + RSI momentum + price above EMAs ───────────
    if rs_pct > 5.0 and rsi > 55 and ema_al == 1:
        reason = (
            f"Outpacing market +{rs_pct:.1f}% · "
            f"RSI {rsi:.0f} · Above 50-EMA"
        )
        return "LEADER", reason

    return "NEUTRAL", ""


# ── Main pipeline ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MarketPulse India — Prediction Engine")
    parser.add_argument("--backtest-weeks", type=int, default=52,
                        help="Number of historical weeks for accuracy backtest (default: 52)")
    parser.add_argument("--force-download", action="store_true",
                        help="Force re-download of OHLCV data (ignore cache)")
    parser.add_argument("--no-backtest", action="store_true",
                        help="Skip walk-forward accuracy backtest (faster, predictions only)")
    parser.add_argument("--prefer-rules", action="store_true",
                        help="Force rule-based model even if model.pkl exists")
    args = parser.parse_args()

    t0 = time.time()
    log.info("=" * 65)
    log.info("  MarketPulse India — Prediction Engine")
    log.info("=" * 65)

    regime       = load_regime()
    prefer_ml    = not args.prefer_rules
    method_used  = "rule_based"

    # ── Step 1: Load OHLCV (reuse backtest.py infrastructure) ────────────────
    # NOTE: importlib is required because the backtest/ directory package
    # shadows the backtest.py module when doing a plain `import backtest`.
    import importlib.util
    spec = importlib.util.spec_from_file_location("backtest_mod", Path("backtest.py"))
    bt_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bt_mod)
    load_ohlcv = bt_mod.load_ohlcv

    try:
        ohlcv = load_ohlcv(force_download=args.force_download)
        log.info(f"[OK] OHLCV loaded: {ohlcv.shape[1]//5} stocks × {len(ohlcv)} days")
    except Exception as exc:
        log.error(f"[FAIL] OHLCV load failed: {exc}")
        log.warning("[WARN] Falling back to ai_picks.json")
        _write_fallback_predictions(regime)
        return

    # ── Step 2: Build feature matrix ─────────────────────────────────────────
    from prediction.features import build_feature_matrix
    try:
        log.info("\n[STEP 2] Building weekly feature matrix...")
        features_df = build_feature_matrix(ohlcv, as_of_date=None)
        if features_df.empty:
            raise ValueError("Feature matrix is empty")
        log.info(f"[OK] Features: {len(features_df)} stocks × {len(features_df.columns)} features")
    except Exception as exc:
        log.error(f"[FAIL] Feature engineering failed: {exc}")
        _write_fallback_predictions(regime)
        return

    # ── Step 3: Check RF retraining ──────────────────────────────────────────
    if prefer_ml:
        from prediction.trainer import should_retrain, train_walk_forward
        from prediction.features import build_historical_feature_label_dataset
        try:
            last_acc = _load_last_accuracy()
            if should_retrain(regime, last_acc):
                log.info("\n[STEP 3] Training RF model (walk-forward)...")
                hist_df = build_historical_feature_label_dataset(
                    ohlcv, backtest_weeks=args.backtest_weeks
                )
                if not hist_df.empty and len(hist_df) >= 500:
                    result = train_walk_forward(hist_df, regime=regime)
                    if result:
                        method_used = "random_forest"
                        log.info(
                            f"[OK] RF model trained "
                            f"(accuracy: {result['training_accuracy_pct']}%)"
                        )
                else:
                    log.info(
                        f"[INFO] Insufficient training data ({len(hist_df)} examples < 500) "
                        f"— using rule-based"
                    )
            else:
                method_used = "random_forest"
        except Exception as exc:
            log.warning(f"[WARN] RF training check failed ({exc}) — using rule-based")

    # ── Step 4: Generate predictions ─────────────────────────────────────────
    from prediction.model import predict_next_week
    try:
        log.info(f"\n[STEP 4] Generating next-week predictions ({method_used})...")
        preds_df = predict_next_week(features_df, regime=regime, prefer_ml=prefer_ml)
        log.info(
            f"[OK] Predictions: BUY={( preds_df.prediction=='BUY').sum()}  "
            f"SELL={(preds_df.prediction=='SELL').sum()}  "
            f"HOLD={(preds_df.prediction=='HOLD').sum()}"
        )
    except Exception as exc:
        log.error(f"[FAIL] Prediction model failed: {exc}")
        _write_fallback_predictions(regime)
        return

    # ── Build predictions.json payload ────────────────────────────────────
    close_prices = {}
    try:
        close_prices = ohlcv["Close"].iloc[-1].to_dict()
    except Exception:
        pass

    prediction_records = []
    for ticker, row in preds_df.iterrows():
        raw_price = close_prices.get(ticker, 0)
        price     = _safe_float(raw_price, default=0, ndigits=2)
        pred      = str(row["prediction"])
        atr_pct   = _safe_float(row.get("atr_pct", 3.0) if "atr_pct" in preds_df.columns
                                 else features_df.loc[ticker, "atr_pct"]
                                 if ticker in features_df.index else 3.0, default=3.0)

        # ── TP / SL / R:R calculation ────────────────────────────────────────
        sl_pct, tp_pct, sl_price, tp_price, rr = None, None, None, None, None
        if pred == "BUY" and price and price > 0:
            sl_pct   = round(atr_pct * 1.5, 2)                              # SL = 1.5× ATR
            tp_pct   = round(sl_pct * 3.0, 2)                               # TP = 3× SL → R:R 1:3
            rr       = round(tp_pct / sl_pct, 1) if sl_pct else 3.0
            sl_price = round(price * (1 - sl_pct / 100), 2)
            tp_price = round(price * (1 + tp_pct / 100), 2)
        elif pred == "SELL" and price and price > 0:
            sl_pct   = round(atr_pct * 1.5, 2)
            tp_pct   = round(sl_pct * 2.0, 2)
            rr       = 2.0

        # ── State classification (SQUEEZE / QUIET / LEADER / NEUTRAL) ─────────
        state, state_reason = "NEUTRAL", ""
        if ticker in features_df.index:
            state, state_reason = classify_stock_state(features_df.loc[ticker])

        rec = {
            "ticker":              ticker,
            "prediction":          pred,
            "confidence":          int(row["confidence"]),
            "expected_return_pct": _safe_float(row["expected_return_pct"]),
            "price":               price,
            # Risk management fields (P3)
            "sl_pct":              sl_pct,
            "tp_pct":              tp_pct,
            "sl_price":            sl_price,
            "tp_price":            tp_price,
            "rr":                  rr,
            # State classification (P4)
            "state":               state,
            "state_reason":        state_reason,
            # Professional signal features (P3)
            "bb_squeeze":     int(features_df.loc[ticker, "bb_squeeze"])
                              if ticker in features_df.index and "bb_squeeze" in features_df.columns
                              else None,
            "vol_contraction": int(features_df.loc[ticker, "vol_contraction"])
                               if ticker in features_df.index and "vol_contraction" in features_df.columns
                               else None,
            "sector_rs_pct":  _safe_float(features_df.loc[ticker, "sector_rs_pct"], ndigits=2)
                               if ticker in features_df.index and "sector_rs_pct" in features_df.columns
                               else None,
            "reasoning":           row["reasoning"],
        }
        prediction_records.append(rec)


    # Sort: BUY by confidence desc, then SELL, then HOLD
    order = {"BUY": 0, "SELL": 1, "HOLD": 2}
    prediction_records.sort(
        key=lambda r: (order[r["prediction"]], -r["confidence"])
    )

    summary_counts = {k: 0 for k in ["BUY", "SELL", "HOLD"]}
    for r in prediction_records:
        summary_counts[r["prediction"]] += 1

    predictions_output = {
        "generated":    datetime.now().strftime("%d %b %Y"),
        "run_at":       datetime.now().strftime("%Y-%m-%d %H:%M"),
        "regime":       regime,
        "method":       method_used,
        "total_stocks": len(prediction_records),
        "summary": {
            "buy":              summary_counts["BUY"],
            "sell":             summary_counts["SELL"],
            "hold":             summary_counts["HOLD"],
            "avg_confidence":   round(
                float(preds_df["confidence"].mean()), 1
            ) if len(preds_df) else 0,
        },
        "predictions": prediction_records,
    }

    with open(PREDICTIONS_OUT, "w", encoding="utf-8") as fh:
        json.dump(predictions_output, fh, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    log.info(
        f"[OK] predictions.json → {PREDICTIONS_OUT} "
        f"({PREDICTIONS_OUT.stat().st_size // 1024} KB)"
    )

    # ── Step 5: Walk-forward accuracy backtest ────────────────────────────────
    if args.no_backtest:
        log.info("\n[SKIP] --no-backtest flag set — skipping accuracy backtest")
        _write_empty_accuracy(regime, method_used)
        _print_summary(t0, prediction_records, None)
        return

    from backtest.walk_forward import run_prediction_backtest
    from backtest.metrics import compute_accuracy_metrics, compute_benchmarks
    try:
        log.info(f"\n[STEP 5] Walk-forward accuracy backtest ({args.backtest_weeks} weeks)...")
        bt_results = run_prediction_backtest(
            ohlcv,
            backtest_weeks=args.backtest_weeks,
            regime=regime,
            prefer_ml=prefer_ml,
        )
    except Exception as exc:
        log.error(f"[FAIL] Accuracy backtest failed: {exc}")
        bt_results = []

    # ── Step 6: Metrics + benchmarks ──────────────────────────────────────────
    try:
        acc_metrics  = compute_accuracy_metrics(bt_results)
        benchmarks   = compute_benchmarks(bt_results)
    except Exception as exc:
        log.error(f"[FAIL] Metrics computation failed: {exc}")
        acc_metrics  = {}
        benchmarks   = {}

    # ── Write prediction_accuracy.json ────────────────────────────────────────
    accuracy_output = {
        "generated":     datetime.now().strftime("%d %b %Y"),
        "run_at":        datetime.now().strftime("%Y-%m-%d %H:%M"),
        "backtest_weeks": args.backtest_weeks,
        "regime":         regime,
        "method":         method_used,
        "accuracy":       acc_metrics,
        "benchmarks":     benchmarks,
    }

    with open(PRED_ACCURACY_OUT, "w", encoding="utf-8") as fh:
        json.dump(accuracy_output, fh, indent=2, ensure_ascii=False, default=str, allow_nan=False)
    log.info(
        f"[OK] prediction_accuracy.json → {PRED_ACCURACY_OUT} "
        f"({PRED_ACCURACY_OUT.stat().st_size // 1024} KB)"
    )

    _print_summary(t0, prediction_records, acc_metrics)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_float(value, default=None, ndigits: int | None = None):
    """Convert a value to a JSON-safe float, replacing NaN/Inf with `default`."""
    try:
        f = float(value)
        if not (f == f) or f in (float("inf"), float("-inf")):
            # NaN check: NaN != NaN is True
            return default
        return round(f, ndigits) if ndigits is not None else f
    except (TypeError, ValueError):
        return default


def _load_last_accuracy() -> float | None:
    if PRED_ACCURACY_OUT.exists():
        try:
            with open(PRED_ACCURACY_OUT, encoding="utf-8") as fh:
                d = json.load(fh)
            return d.get("accuracy", {}).get("overall_accuracy_pct")
        except Exception:
            pass
    return None


def _write_fallback_predictions(regime: str):
    log.warning("[FALLBACK] Writing degraded predictions from ai_picks.json...")
    fallback_preds = fallback_from_ai_picks(regime)
    if not fallback_preds:
        fallback_preds = []
    summary_counts = {"BUY": 0, "SELL": 0, "HOLD": 0}
    for r in fallback_preds:
        summary_counts[r["prediction"]] = summary_counts.get(r["prediction"], 0) + 1

    out = {
        "generated":    datetime.now().strftime("%d %b %Y"),
        "run_at":       datetime.now().strftime("%Y-%m-%d %H:%M"),
        "regime":       regime,
        "method":       "fallback_ai_score",
        "total_stocks": len(fallback_preds),
        "summary":      {k.lower(): v for k, v in summary_counts.items()},
        "predictions":  fallback_preds,
    }
    with open(PREDICTIONS_OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"), ensure_ascii=False)
    log.info(f"[OK] Fallback predictions.json written ({len(fallback_preds)} stocks)")


def _write_empty_accuracy(regime: str, method: str):
    out = {
        "generated":     datetime.now().strftime("%d %b %Y"),
        "run_at":        datetime.now().strftime("%Y-%m-%d %H:%M"),
        "backtest_weeks": 0,
        "regime":         regime,
        "method":         method,
        "accuracy":       {},
        "benchmarks":     {},
    }
    with open(PRED_ACCURACY_OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    log.info("[OK] Empty prediction_accuracy.json written")


def _print_summary(t0: float, preds: list, acc: dict | None):
    elapsed = time.time() - t0
    buys  = sum(1 for r in preds if r["prediction"] == "BUY")
    sells = sum(1 for r in preds if r["prediction"] == "SELL")
    holds = sum(1 for r in preds if r["prediction"] == "HOLD")

    log.info("\n" + "=" * 65)
    log.info("  PREDICTION ENGINE COMPLETE")
    log.info("=" * 65)
    log.info(f"  Stocks predicted  : {len(preds):,}")
    log.info(f"  BUY signals       : {buys:,}")
    log.info(f"  SELL signals      : {sells:,}")
    log.info(f"  HOLD signals      : {holds:,}")
    if acc:
        log.info(f"  Overall accuracy  : {acc.get('overall_accuracy_pct', '—')}%")
        log.info(f"  BUY precision     : {acc.get('precision', {}).get('buy_pct', '—')}%")
        log.info(f"  SELL precision    : {acc.get('precision', {}).get('sell_pct', '—')}%")
    log.info(f"  Elapsed           : {elapsed:.1f}s")
    log.info(f"  Outputs           : {PREDICTIONS_OUT}  {PRED_ACCURACY_OUT}")
    log.info("=" * 65)


if __name__ == "__main__":
    main()
