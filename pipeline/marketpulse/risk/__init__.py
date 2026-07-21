"""
MarketPulse — Risk Manager

Handles position sizing and portfolio-level risk controls.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from marketpulse.config.settings import (
    CAPITAL,
    MAX_POSITIONS,
    MAX_SECTOR_EXPOSURE_PCT,
    RISK_PER_TRADE_PCT,
    WEEKLY_DRAWDOWN_CAP_PCT,
)

log = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents one open position in the portfolio."""

    ticker: str
    sector: str
    qty: int
    entry_price: float
    stop_loss: float
    entry_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    @property
    def cost_basis(self) -> float:
        """Total capital at risk (entry x qty)."""
        return self.entry_price * self.qty

    @property
    def risk_amount(self) -> float:
        """Max loss this position can incur (SL distance x qty)."""
        return (self.entry_price - self.stop_loss) * self.qty

    def unrealized_pnl(self, current_price: float) -> float:
        """P&L at a given mark-to-market price."""
        return (current_price - self.entry_price) * self.qty


class RiskManager:
    """
    Stateful portfolio risk manager.

    Tracks open positions, enforces position limits, sector caps, and
    weekly drawdown guards.
    """

    def __init__(self, capital: float = float(CAPITAL)) -> None:
        self._initial_capital = capital
        self._capital = capital
        self._positions: dict[str, Position] = {}

        # Weekly tracking (reset each Monday)
        self._week_start_capital = capital
        self._weekly_pnl = 0.0
        self._weekly_trades = 0
        self._halted = False  # True if weekly DD cap breached

        # Lifetime tracking
        self._total_trades = 0
        self._total_pnl = 0.0
        self._trade_history: list[dict[str, Any]] = []

    # ── Position Sizing ──────────────────────────────────────────────────

    def position_size(
        self,
        entry_price: float,
        sl_distance: float,
        regime_mult: float = 1.0,
    ) -> int:
        """
        Compute share quantity using the risk-per-trade formula.

            risk_amount = capital x RISK_PER_TRADE_PCT / 100 x regime_mult
            qty = risk_amount / sl_distance
        """
        if sl_distance <= 0:
            log.warning("SL distance <= 0 — defaulting to 1 share")
            return 1

        risk_amount = self._capital * (RISK_PER_TRADE_PCT / 100) * regime_mult
        qty = int(risk_amount / sl_distance)
        qty = max(1, qty)

        # Sanity: single position shouldn't exceed 20% of capital
        max_position_value = self._capital * 0.20
        if entry_price * qty > max_position_value:
            qty = max(1, int(max_position_value / entry_price))

        return qty

    # ── Position Gates ───────────────────────────────────────────────────

    def can_add_position(self, ticker: str, sector: str = "") -> tuple[bool, str]:
        """
        Check all portfolio-level gates before opening a new position.
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
                return (
                    False,
                    f"sector cap ({MAX_SECTOR_EXPOSURE_PCT}%) reached for {sector}",
                )

        return True, ""

    def _sector_exposure_pct(self, sector: str) -> float:
        """Return current % of capital allocated to a specific sector."""
        if not self._positions or self._capital <= 0:
            return 0.0
        sector_value = sum(p.cost_basis for p in self._positions.values() if p.sector == sector)
        return sector_value / self._capital * 100

    # ── Position Lifecycle ───────────────────────────────────────────────

    def add_position(
        self,
        ticker: str,
        sector: str,
        qty: int,
        entry_price: float,
        stop_loss: float,
    ) -> bool:
        """
        Open a new position if all gates pass.
        """
        ok, reason = self.can_add_position(ticker, sector)
        if not ok:
            log.debug("Position rejected %s: %s", ticker, reason)
            return False

        self._positions[ticker] = Position(
            ticker=ticker,
            sector=sector,
            qty=qty,
            entry_price=entry_price,
            stop_loss=stop_loss,
        )
        self._weekly_trades += 1
        self._total_trades += 1
        log.debug(
            "Position opened: %s qty=%d entry=%s SL=%s",
            ticker,
            qty,
            entry_price,
            stop_loss,
        )
        return True

    def close_position(self, ticker: str, exit_price: float, exit_reason: str = "") -> float:
        """
        Close an existing position.
        """
        if ticker not in self._positions:
            log.warning("close_position: %s not in portfolio", ticker)
            return 0.0

        pos = self._positions.pop(ticker)
        pnl = (exit_price - pos.entry_price) * pos.qty

        self._capital += pnl
        self._weekly_pnl += pnl
        self._total_pnl += pnl

        # Record in history
        self._trade_history.append(
            {
                "ticker": ticker,
                "sector": pos.sector,
                "entry_date": pos.entry_date,
                "exit_date": datetime.now().strftime("%Y-%m-%d"),
                "entry_price": round(pos.entry_price, 2),
                "exit_price": round(exit_price, 2),
                "qty": pos.qty,
                "pnl": round(pnl, 2),
                "return_pct": round((exit_price - pos.entry_price) / pos.entry_price * 100, 3),
                "exit_reason": exit_reason,
            }
        )

        # Check weekly drawdown guard after each close
        self._check_weekly_drawdown()

        log.debug(
            "Position closed: %s exit=%s pnl=%+,.0f [%s]",
            ticker,
            exit_price,
            pnl,
            exit_reason,
        )
        return pnl

    def close_all(self, price_map: dict[str, float]) -> float:
        """Close all open positions at specified prices. Returns total P&L."""
        total = 0.0
        for ticker in list(self._positions.keys()):
            price = price_map.get(ticker, self._positions[ticker].entry_price)
            total += self.close_position(ticker, price, "FORCE_CLOSE")
        return total

    # ── Drawdown Guard ───────────────────────────────────────────────────

    def _check_weekly_drawdown(self) -> None:
        """Set halt flag if weekly P&L loss exceeds the cap."""
        if self._week_start_capital <= 0:
            return
        weekly_dd_pct = -self._weekly_pnl / self._week_start_capital * 100
        if weekly_dd_pct >= WEEKLY_DRAWDOWN_CAP_PCT:
            if not self._halted:
                log.warning(
                    "Weekly drawdown cap triggered: -%.1f%% (cap=%s%%) — no new positions",
                    weekly_dd_pct,
                    WEEKLY_DRAWDOWN_CAP_PCT,
                )
            self._halted = True

    def weekly_drawdown_guard(self) -> bool:
        """Returns True if new trades are allowed (drawdown cap not hit)."""
        return not self._halted

    # ── Week Reset ───────────────────────────────────────────────────────

    def reset_week(self) -> None:
        """
        Call at the start of each new trading week.
        Resets weekly counters whilst preserving open positions and lifetime P&L.
        """
        self._week_start_capital = self._capital
        self._weekly_pnl = 0.0
        self._weekly_trades = 0
        self._halted = False

    # ── State / Reporting ────────────────────────────────────────────────

    @property
    def capital(self) -> float:
        return self._capital

    @property
    def open_positions_count(self) -> int:
        return len(self._positions)

    @property
    def open_positions(self) -> dict[str, Position]:
        return dict(self._positions)

    def portfolio_value(self, price_map: dict[str, float] | None = None) -> float:
        """
        Mark-to-market portfolio value.
        """
        if price_map is None:
            return self._capital + sum(p.cost_basis for p in self._positions.values())
        return self._capital + sum(
            p.unrealized_pnl(price_map.get(p.ticker, p.entry_price))
            for p in self._positions.values()
        )

    def get_state(self) -> dict[str, Any]:
        """Return a serializable snapshot of current portfolio state."""
        return {
            "capital": round(self._capital, 2),
            "initial_capital": self._initial_capital,
            "total_pnl": round(self._total_pnl, 2),
            "total_return_pct": round(self._total_pnl / self._initial_capital * 100, 2),
            "open_positions": len(self._positions),
            "max_positions": MAX_POSITIONS,
            "weekly_pnl": round(self._weekly_pnl, 2),
            "weekly_trades": self._weekly_trades,
            "weekly_halted": self._halted,
            "total_trades": self._total_trades,
            "positions": [
                {
                    "ticker": p.ticker,
                    "sector": p.sector,
                    "qty": p.qty,
                    "entry_price": p.entry_price,
                    "stop_loss": p.stop_loss,
                    "cost_basis": round(p.cost_basis, 2),
                    "risk_amount": round(p.risk_amount, 2),
                }
                for p in self._positions.values()
            ],
        }

    def get_trade_history(self) -> list[dict[str, Any]]:
        """Returns the full closed-trade history."""
        return list(self._trade_history)

    def __repr__(self) -> str:
        return (
            f"RiskManager(capital={self._capital:,.0f}, "
            f"positions={len(self._positions)}/{MAX_POSITIONS}, "
            f"weekly_pnl={self._weekly_pnl:+,.0f}, "
            f"halted={self._halted})"
        )
