"""
MarketPulse India — Opportunity Data Models

Plain dataclasses used as the lingua franca between scanners and engine.
No business logic here — just typed containers.
"""

from dataclasses import dataclass, field


@dataclass
class ScanResult:
    """Output of one scanner for one ticker."""
    ticker:     str
    scanner:    str           # scanner name e.g. "52W_BREAKOUT"
    triggered:  bool = False
    score:      int  = 0      # 0–max_score for this scanner
    signals:    list[str] = field(default_factory=list)
    indicators: dict = field(default_factory=dict)


@dataclass
class Opportunity:
    """
    Final fused output for one ticker after all scanners run.
    Written directly to opportunities.json.
    """
    ticker:      str
    rank:        int
    score:       int                         # 0–100 (+ multi-signal bonus)
    signals:     list[str] = field(default_factory=list)
    indicators:  dict      = field(default_factory=dict)
    fundamental: dict      = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ticker":      self.ticker,
            "rank":        self.rank,
            "score":       self.score,
            "signals":     self.signals,
            "indicators":  self.indicators,
            "fundamental": self.fundamental,
        }
