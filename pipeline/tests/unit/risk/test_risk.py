"""
Unit tests for marketpulse.risk — portfolio risk manager.
"""

from __future__ import annotations

from marketpulse.risk import Position, RiskManager


def test_position_properties() -> None:
    pos = Position(
        ticker="RELIANCE",
        sector="Energy",
        qty=100,
        entry_price=2500.0,
        stop_loss=2400.0,
    )
    assert pos.cost_basis == 250000.0
    assert pos.risk_amount == 10000.0
    assert pos.unrealized_pnl(2600.0) == 10000.0
    assert pos.unrealized_pnl(2450.0) == -5000.0


def test_risk_manager_initial_state() -> None:
    rm = RiskManager(capital=1000000.0)
    assert rm.capital == 1000000.0
    assert rm.open_positions_count == 0
    assert rm.weekly_drawdown_guard() is True


def test_risk_manager_position_sizing() -> None:
    rm = RiskManager(capital=1000000.0)
    # Risk per trade: 1.5% of 1000000 = 15000
    # Stop loss distance: 50 -> Qty = 15000 / 50 = 300
    # Cost basis: 300 * 500 = 150000 (less than 20% of capital, i.e. 200000)
    qty = rm.position_size(entry_price=500.0, sl_distance=50.0)
    assert qty == 300

    # Check limit of 20% value: 20% of 1000000 = 200000
    # Entry price 1000, 300 shares is 300000 (too high)
    # Max shares should be 200000 / 1000 = 200
    qty_high_entry = rm.position_size(entry_price=1000.0, sl_distance=5.0)
    assert qty_high_entry == 200


def test_risk_manager_gates() -> None:
    rm = RiskManager(capital=1000000.0)

    # Can add position
    ok, reason = rm.can_add_position("TCS", "Technology")
    assert ok is True

    # Max 5 positions
    for i, ticker in enumerate(["P1", "P2", "P3", "P4", "P5"]):
        added = rm.add_position(ticker, "Tech", 10, 100.0, 90.0)
        assert added is True

    ok, reason = rm.can_add_position("P6", "Tech")
    assert ok is False
    assert "max positions" in reason


def test_risk_manager_sector_cap() -> None:
    rm = RiskManager(capital=1000000.0)

    # Max sector exposure is 30% of capital (300000)
    # Add position costing 250000 in Energy
    rm.add_position("RELIANCE", "Energy", 100, 2500.0, 2400.0)
    ok, reason = rm.can_add_position("ONGC", "Energy")
    assert ok is True  # Cost basis of ONGC not yet added

    # Now add ONGC costing another 100000 (total Energy = 350000 > 30% of 1M)
    # Sizing ONGC so that it exceeds 30% sector cap
    rm.add_position("ONGC", "Energy", 100, 1000.0, 900.0)

    ok, reason = rm.can_add_position("BPCL", "Energy")
    assert ok is False
    assert "sector cap" in reason


def test_risk_manager_drawdown_guard() -> None:
    rm = RiskManager(capital=1000000.0)

    # Open and close position with a large loss (> 5% of weekly capital, i.e. > 50000)
    rm.add_position("LOSER", "Tech", 1000, 100.0, 90.0)
    # Close at 40 (Loss: 60 * 1000 = 60000)
    pnl = rm.close_position("LOSER", 40.0, "SL")
    assert pnl == -60000.0

    assert rm.weekly_drawdown_guard() is False

    # Try adding new position: should be blocked by weekly DD cap
    ok, reason = rm.can_add_position("NEW", "Tech")
    assert ok is False
    assert "weekly drawdown cap" in reason

    # Reset week should clear it
    rm.reset_week()
    assert rm.weekly_drawdown_guard() is True
