"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  MarketPulse India — Risk Manager                                           ║
║                                                                              ║
║  Handles position sizing and portfolio-level risk controls.                  ║
║                                                                              ║
║  Position sizing formula:                                                    ║
║    qty = (capital × risk_per_trade_pct / 100) / stop_loss_distance          ║
║                                                                              ║
║  Portfolio rules:                                                            ║
║    - Max 5 concurrent open positions                                         ║
║    - Max 30% capital in any one sector                                       ║
║    - Halt new trades if weekly drawdown > 5%                                 ║
║                                                                              ║
║  Public API:                                                                 ║
║    rm = RiskManager(capital=1_000_000)                                       ║
║    rm.position_size(entry, sl_distance, regime_mult)  → int (qty)           ║
║    rm.can_add_position(ticker, sector)                → bool                 ║
║    rm.add_position(ticker, sector, qty, entry, sl)                           ║
║    rm.close_position(ticker, exit_price)              → pnl float           ║
║    rm.weekly_drawdown_guard()                         → bool (True=ok)       ║
║    rm.get_state()                                     → dict                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config.settings import (
    CAPITAL,
    MAX_POSITIONS,
    MAX_SECTOR_EXPOSURE_PCT,
    RISK_PER_TRADE_PCT,
    WEEKLY_DRAWDOWN_CAP_PCT,
)

log = logging.getLogger("risk_manager")


@dataclass
class Position:
    """Represents one open position in the portfolio."""
    ticker:       str
    sector:       str
    qty:          int
    entry_price:  float
    stop_loss:    float
    entry_date:   str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    @property
    def cost_basis(self) -> float:
        """Total capital at risk (entry × qty)."""
        return self.entry_price * self.qty

    @property
    def risk_amount(self) -> float:
        """Max loss this position can incur (SL distance × qty)."""
        return (self.entry_price - self.stop_loss) * self.qty

    def unrealized_pnl(self, current_price: float) -> float:
        """P&L at a given mark-to-market price."""
        return (current_price - self.entry_price) * self.qty


class RiskManager:
    """
    Stateful portfolio risk manager.

    Tracks open positions, enforces position limits, sector caps, and
    weekly drawdown guards. Designed to work with both the backtest engine
    and live trade management.

    State is reset each week (call reset_week() at the start of each
    backtest week or each Monday in live trading).
    """

    def __init__(self, capital: float = CAPITAL):
        self._initial_capital = capital
        self._capital         = capital
        self._positions: dict[str, Position] = {}

        # Weekly tracking (reset each Monday)
        self._week_start_capital = capital
        self._weekly_pnl         = 0.0
        self._weekly_trades      = 0
        self._halted             = False   # True if weekly DD cap breached

        # Lifetime tracking
        self._total_trades   = 0
        self._total_pnl      = 0.0
        self._trade_history: list[dict] = []

    # ══════════════════════════════════════════════════════════════════
    #  POSITION SIZING
    # ══════════════════════════════════════════════════════════════════

    def position_size(
        self,
        entry_price:    float,
        sl_distance:    float,
        regime_mult:    float = 1.0,
    ) -> int:
        """
        Compute share quantity using the risk-per-trade formula.

            risk_amount = capital × RISK_PER_TRADE_PCT / 100 × regime_mult
            qty = risk_amount / sl_distance

        Args:
            entry_price:  Planned entry price (used for sanity checks)
            sl_distance:  Absolute price distance from entry to stop loss
            regime_mult:  Scaling factor from RegimeFilter (0.25 – 1.0)

        Returns:
            Integer share quantity (minimum 1)
        """
        if sl_distance <= 0:
            log.warning("  SL distance <= 0 — defaulting to 1 share")
            return 1

        risk_amount = self._capital * (RISK_PER_TRADE_PCT / 100) * regime_mult
        qty = int(risk_amount / sl_distance)
        qty = max(1, qty)

        # Sanity: single position shouldn't exceed 20% of capital
        max_position_value = self._capital * 0.20
        if entry_price * qty > max_position_value:
            qty = max(1, int(max_position_value / entry_price))

        return qty

    # ══════════════════════════════════════════════════════════════════
    #  POSITION GATES
    # ══════════════════════════════════════════════════════════════════

    def can_add_position(self, ticker: str, sector: str = "") -> tuple[bool, str]:
        """
        Check all portfolio-level gates before opening a new position.

        Returns:
            (True, "") if position can be opened
            (False, reason_string) if blocked
        """
        # Gate 1: Weekly drawdown halt
        if self._halted:
            return False, f"weekly drawdown cap ({WEEKLY_DRAWDOWN_CAP_PCT}%) reached"

        # Gate 2: Already in this ticker
        if ticker in self._positions:
            return False, f"already holding {ticker}"

        # Gate 3: Max concurrent positions
        if len(self._positions) >= MAX_POSITIONS:
            return False, f"max positions ({MAX_POSITIONS}) reached"

        # Gate 4: Sector exposure cap
        if sector:
            sector_exposure = self._sector_exposure_pct(sector)
            if sector_exposure >= MAX_SECTOR_EXPOSURE_PCT:
                return False, f"sector cap ({MAX_SECTOR_EXPOSURE_PCT}%) reached for {sector}"

        return True, ""

    def _sector_exposure_pct(self, sector: str) -> float:
        """Return current % of capital allocated to a specific sector."""
        if not self._positions or self._capital <= 0:
            return 0.0
        sector_value = sum(
            p.cost_basis
            for p in self._positions.values()
            if p.sector == sector
        )
        return sector_value / self._capital * 100

    # ══════════════════════════════════════════════════════════════════
    #  POSITION LIFECYCLE
    # ══════════════════════════════════════════════════════════════════

    def add_position(
        self,
        ticker:      str,
        sector:      str,
        qty:         int,
        entry_price: float,
        stop_loss:   float,
    ) -> bool:
        """
        Open a new position if all gates pass.
        Returns True if position was added, False if blocked.
        """
        ok, reason = self.can_add_position(ticker, sector)
        if not ok:
            log.debug(f"  Position rejected {ticker}: {reason}")
            return False

        self._positions[ticker] = Position(
            ticker      = ticker,
            sector      = sector,
            qty         = qty,
            entry_price = entry_price,
            stop_loss   = stop_loss,
        )
        self._weekly_trades += 1
        self._total_trades  += 1
        log.debug(
            f"  Position opened: {ticker}  qty={qty}"
            f"  entry={entry_price}  SL={stop_loss}"
        )
        return True

    def close_position(self, ticker: str, exit_price: float, exit_reason: str = "") -> float:
        """
        Close an existing position.

        Updates capital, weekly P&L, and trade history.
        Returns realized P&L (negative = loss).
        """
        if ticker not in self._positions:
            log.warning(f"  close_position: {ticker} not in portfolio")
            return 0.0

        pos = self._positions.pop(ticker)
        pnl = (exit_price - pos.entry_price) * pos.qty

        self._capital      += pnl
        self._weekly_pnl   += pnl
        self._total_pnl    += pnl

        # Record in history
        self._trade_history.append({
            "ticker":       ticker,
            "sector":       pos.sector,
            "entry_date":   pos.entry_date,
            "exit_date":    datetime.now().strftime("%Y-%m-%d"),
            "entry_price":  round(pos.entry_price, 2),
            "exit_price":   round(exit_price, 2),
            "qty":          pos.qty,
            "pnl":          round(pnl, 2),
            "return_pct":   round((exit_price - pos.entry_price) / pos.entry_price * 100, 3),
            "exit_reason":  exit_reason,
        })

        # Check weekly drawdown guard after each close
        self._check_weekly_drawdown()

        log.debug(
            f"  Position closed: {ticker}  exit={exit_price}"
            f"  pnl={pnl:+,.0f}  [{exit_reason}]"
        )
        return pnl

    def close_all(self, price_map: dict[str, float]) -> float:
        """Close all open positions at specified prices. Returns total P&L."""
        total = 0.0
        for ticker in list(self._positions.keys()):
            price = price_map.get(ticker, self._positions[ticker].entry_price)
            total += self.close_position(ticker, price, "FORCE_CLOSE")
        return total

    # ══════════════════════════════════════════════════════════════════
    #  DRAWDOWN GUARD
    # ══════════════════════════════════════════════════════════════════

    def _check_weekly_drawdown(self) -> None:
        """Set halt flag if weekly P&L loss exceeds the cap."""
        if self._week_start_capital <= 0:
            return
        weekly_dd_pct = -self._weekly_pnl / self._week_start_capital * 100
        if weekly_dd_pct >= WEEKLY_DRAWDOWN_CAP_PCT:
            if not self._halted:
                log.warning(
                    f"  Weekly drawdown cap triggered: "
                    f"-{weekly_dd_pct:.1f}% (cap={WEEKLY_DRAWDOWN_CAP_PCT}%)"
                    f" — no new positions this week"
                )
            self._halted = True

    def weekly_drawdown_guard(self) -> bool:
        """Returns True if new trades are allowed (drawdown cap not hit)."""
        return not self._halted

    # ══════════════════════════════════════════════════════════════════
    #  WEEK RESET
    # ══════════════════════════════════════════════════════════════════

    def reset_week(self) -> None:
        """
        Call at the start of each new trading week (each Monday).
        Resets weekly counters whilst preserving open positions and lifetime P&L.
        """
        self._week_start_capital = self._capital
        self._weekly_pnl         = 0.0
        self._weekly_trades      = 0
        self._halted             = False

    # ══════════════════════════════════════════════════════════════════
    #  STATE / REPORTING
    # ══════════════════════════════════════════════════════════════════

    @property
    def capital(self) -> float:
        return self._capital

    @property
    def open_positions_count(self) -> int:
        return len(self._positions)

    @property
    def open_positions(self) -> dict[str, Position]:
        return dict(self._positions)

    def portfolio_value(self, price_map: dict[str, float] = None) -> float:
        """
        Mark-to-market portfolio value.
        If price_map not supplied, uses entry prices (cost basis).
        """
        if price_map is None:
            return self._capital + sum(p.cost_basis for p in self._positions.values())
        return self._capital + sum(
            p.unrealized_pnl(price_map.get(p.ticker, p.entry_price))
            for p in self._positions.values()
        )

    def get_state(self) -> dict:
        """Return a serializable snapshot of current portfolio state."""
        return {
            "capital":            round(self._capital, 2),
            "initial_capital":    self._initial_capital,
            "total_pnl":          round(self._total_pnl, 2),
            "total_return_pct":   round(self._total_pnl / self._initial_capital * 100, 2),
            "open_positions":     len(self._positions),
            "max_positions":      MAX_POSITIONS,
            "weekly_pnl":         round(self._weekly_pnl, 2),
            "weekly_trades":      self._weekly_trades,
            "weekly_halted":      self._halted,
            "total_trades":       self._total_trades,
            "positions": [
                {
                    "ticker":      p.ticker,
                    "sector":      p.sector,
                    "qty":         p.qty,
                    "entry_price": p.entry_price,
                    "stop_loss":   p.stop_loss,
                    "cost_basis":  round(p.cost_basis, 2),
                    "risk_amount": round(p.risk_amount, 2),
                }
                for p in self._positions.values()
            ],
        }

    def get_trade_history(self) -> list[dict]:
        """Returns the full closed-trade history."""
        return list(self._trade_history)

    def __repr__(self) -> str:
        return (
            f"RiskManager(capital={self._capital:,.0f}, "
            f"positions={len(self._positions)}/{MAX_POSITIONS}, "
            f"weekly_pnl={self._weekly_pnl:+,.0f}, "
            f"halted={self._halted})"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  CLI  — quick self-test: python risk_manager.py
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    rm = RiskManager(capital=1_000_000)

    print("\nRiskManager self-test")
    print(f"  Initial capital: {rm.capital:,.0f}")

    # Test position sizing
    entry    = 1500.0
    sl_dist  = 37.5    # ATR-based SL of 2.5% = 37.5 on 1500
    qty      = rm.position_size(entry, sl_dist, regime_mult=1.0)
    print(f"\n  Position size test:")
    print(f"    Entry={entry}  SL_dist={sl_dist}  -> qty={qty} shares")
    print(f"    Capital at risk = {sl_dist * qty:,.0f} ({sl_dist * qty / rm.capital * 100:.2f}%)")

    # Test adding positions
    ok = rm.add_position("RELIANCE", "Energy",    qty,  entry, entry - sl_dist)
    ok = rm.add_position("TCS",      "Technology", qty, entry, entry - sl_dist)
    print(f"\n  After 2 positions: {rm}")

    # Test sector cap
    ok, reason = rm.can_add_position("INFY", "Technology")
    print(f"  3rd Technology position: allowed={ok}  reason='{reason}'")

    # Test close
    pnl = rm.close_position("RELIANCE", entry * 1.04, "TP")
    print(f"\n  Closed RELIANCE at +4%: pnl={pnl:+,.0f}  capital={rm.capital:,.0f}")

    print(f"\n  Final state: {rm.get_state()}")


if __name__ == "__main__":
    main()
