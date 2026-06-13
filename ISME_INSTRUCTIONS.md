# Institutional Stage Momentum Engine (ISME)
### A Professional All-in-One Trading System for Indian Equities

---

## Overview

ISME is a **multi-factor overlay indicator** designed for NSE/BSE stocks that combines **Stage Analysis**, **Relative Strength**, **Momentum Triggers**, **Smart Money Detection**, and **Quarterly Fundamentals** into one unified system. Built on the proven methodologies of Mark Minervini and William O'Neil.

**Best timeframe:** Daily | **Market:** Indian Equities (NSE/BSE)

---

## ⚙️ Settings

| Setting | Default | Description |
|---|---|---|
| Length ADX | 14 | ADX calculation period |
| Threshold ADX | 14 | Minimum ADX for trend confirmation |
| Length RSI | 14 | RSI calculation period |
| SAR Start / Inc / Max | 0.02 / 0.02 / 0.2 | Parabolic SAR parameters |
| ATR Multiplier | 2.5 | Stop loss distance (red line below price) |
| RS Index | NSE:NIFTY | Benchmark index for Relative Strength |
| RS MA Period | 10 | RS moving average smoothing |
| **Show Parabolic SAR** | ✅ On | Toggle SAR dots on/off |
| **Show Insider Activity** | ✅ On | Toggle smart money signals |
| **Show Signal Legend** | ❌ Off | Show full signal guide on chart (bottom-left) |
| **Table Font Size** | Normal | Small / Normal / Large for dashboard tables |

> **💡 Tip:** Enable "Show Signal Legend" when first learning — it displays a reference table on the chart explaining every signal.

---

## 🎨 Background Color — Relative Strength

The entire chart background changes color based on the stock's Relative Strength vs NIFTY:

| Background | Meaning | Action |
|---|---|---|
| **🟢 Green tint** | RS above its EMA → Stock is **outperforming** the index | Favour long positions |
| **🔴 Red tint** | RS below its EMA → Stock is **underperforming** the index | Avoid new buys |

---

## 📊 EMA Band (Colored Fill)

A shaded band fills between **EMA 20** (aqua line) and **EMA 50** (orange line):

| Band Color | Meaning |
|---|---|
| **Green fill** | EMA 20 > EMA 50 → Bullish short-term trend |
| **Red fill** | EMA 20 < EMA 50 → Bearish short-term trend |

---

## 🏷️ Stage Label (Top of Chart)

Based on Weinstein/Minervini Stage Analysis:

| Stage | Color | What It Means | Action |
|---|---|---|---|
| **STAGE 2 - ADVANCING** | 🟢 Green | Confirmed uptrend, all EMAs aligned upward | ✅ **Best time to buy** |
| **STAGE 1 - BASE** | ⬜ Gray | Building a base, EMA 200 is flat | ⏳ Watch for breakout |
| **STAGE 3 - DISTRIBUTION** | 🟠 Orange | Price below EMA 150 but above EMA 200 | ⚠️ **Reduce positions** |
| **STAGE 4 - DECLINING** | 🔴 Red | Below EMA 200, downtrend confirmed | 🚫 **Do not buy** |

---

## 📈 Buy Signals (Below Candles)

| Label | Color | Name | Trigger | Strength |
|---|---|---|---|---|
| **A** | 🟢 Green | Trend Breakout | Price > EMA20 > EMA50 + RSI > 55 + ADX > 14 + Minervini template | ⭐⭐⭐ |
| **B** | 🟢 Lime | Donchian Breakout | Price crosses above 20-day high + volume > 20-day average | ⭐⭐ |
| **C** | 🟢 Teal | 52W Breakout | Price at/above 52-week high + RS outperforming index | ⭐⭐⭐ |
| **STRONG** | 🔵 Blue | Multi-Signal | 2 or more of A/B/C trigger simultaneously | ⭐⭐⭐⭐⭐ |

> All signals fire **once per transition** — they appear only on the first bar the condition becomes true, keeping your chart clean.

---

## 📉 Sell Signals (Above Candles)

| Label | Color | Name | Trigger | Urgency |
|---|---|---|---|---|
| **X** | 🔴 Red | Momentum Loss | Price below EMA 20 + RSI < 45 | ⚠️ Early warning |
| **Y** | 🟤 Maroon | Trend Weakness | Price below EMA 50 + RS underperforming | 🔶 Reduce position |
| **Z** | 🟠 Orange | Trend Breakdown | Price below EMA 200 + strong ADX | 🔴 **Exit immediately** |

---

## 🔍 Insider / Smart Money Signals

Detects institutional activity through volume anomaly + price action analysis:

| Label | Color | Name | What It Detects |
|---|---|---|---|
| **ACC** | 🟢 Bright Green | Accumulation | Volume > 2× average + close in upper 60% of bar range + price up |
| **DIST** | 🔴 Bright Red | Distribution | Volume > 2× average + close in lower 40% of bar range + price down |
| **🕵** | 🟣 Purple | Stealth Accumulation | 5-day average volume rising 1.5× quietly while price stays flat near EMA 50 |

**How to use:**
- **ACC** in Stage 2 with green background = Institutions are loading. Strong buy confirmation.
- **DIST** in Stage 3 = Smart money is exiting. Consider reducing exposure.
- **🕵** in Stage 1 = Quiet institutional positioning before a potential breakout. Add to watchlist.

Toggle: Settings → **"Show Insider Activity"**

---

## 🔔 Other Chart Markers

| Shape | Color | Meaning |
|---|---|---|
| **◆ Diamond** (above bar) | 🟠 Orange | Donchian channel breakout — new 20-day high |
| **🔥 52W label** (above bar) | 🟡 Gold | New 52-week high — major breakout level |
| **▲ Triangle** (below bar) | 🟣 Purple | RS new 100-bar high — outperformance peak |
| **+ Cross dots** (on chart) | 🟢/🔴 | Parabolic SAR — green above price (bullish), red below (bearish) |
| **Red line** (below price) | 🔴 | ATR trailing stop — exit if price closes below |

---

## 📋 Dashboard Tables

### Top-Right: Quick Summary
| Row | What It Shows |
|---|---|
| Stage | Current market stage with color indicator |
| RS / RS EMA | Relative Strength value vs its moving average |
| ADX | Trend strength — green if > threshold, red if weak |
| RSI | Momentum — green > 55, gray neutral, red < 45 |
| Sales QoQ | Latest quarter revenue growth vs previous quarter |
| Profit QoQ | Latest quarter profit growth vs previous quarter |
| Mkt Cap | Market capitalization in crores |
| 52W High | Whether stock is at a 52-week high (YES/NO) |

### Bottom-Right: Quarterly Fundamentals
Screener-style table showing the last **5 fiscal quarters**:

| Column | Description |
|---|---|
| **FQ** | Fiscal quarter (e.g., Mar-26, Dec-25, Sep-25) |
| **NP** | Net Profit in ₹ Crores |
| **YoY** | Year-over-Year growth (vs same quarter last year) |
| **QoQ** | Quarter-over-Quarter growth (vs previous quarter) |
| **Sales** | Revenue in ₹ Crores |
| **OPM** | Operating Profit Margin % |

**Color coding:**
- 🟩 Green background = Positive growth
- 🟥 Red background = Negative growth
- Gray = Data not available

### Bottom-Left: Signal Legend (Optional)
Enable via Settings → **"Show Signal Legend"** to display a complete reference guide explaining every signal directly on your chart.

---

## 🏆 Best Entry Scenarios

### Scenario 1: The Perfect Setup ⭐⭐⭐⭐⭐
- Stage = **STAGE 2 - ADVANCING**
- Background = **Green** (RS outperforming NIFTY)
- Signal = **STRONG BUY** label appears
- **ACC** (accumulation) signal nearby
- Volume above 20-day average
- **Action:** Buy with stop at ATR line (red). Trail stop below EMA 20.

### Scenario 2: Breakout Entry ⭐⭐⭐⭐
- Stage = **STAGE 2** or transitioning from **STAGE 1**
- **B** label appears (Donchian breakout with volume)
- 🔥 52W High flag visible
- **Action:** Buy the breakout. Set stop below the breakout candle low.

### Scenario 3: Stealth Entry ⭐⭐⭐
- Stage = **STAGE 1** (basing)
- **🕵** stealth accumulation detected
- RS starting to turn (background flickering green)
- **Action:** Small position size. Add more when **A** signal confirms.

---

## 🚪 Exit Rules

| Step | Signal | Action |
|---|---|---|
| 1 | **X** appears | Tighten stop to EMA 20 |
| 2 | **Y** appears | Reduce position by 50% |
| 3 | **Z** appears | **Exit completely** |
| 4 | Stage changes to 3 or 4 | Exit all positions |
| 5 | Background turns red | Review and exit weak positions |
| 6 | **DIST** with high volume | Smart money exiting — follow them |

---

## ⚠️ Important Notes

- **No repainting:** The 52-week high uses `high[1]` (previous bar's data) to prevent look-ahead bias.
- **Signals fire once:** Buy/Sell labels appear only on the transition bar, not on every qualifying bar.
- **Financial data:** Quarterly fundamentals are sourced from TradingView. Some stocks may show "--" if data is unavailable for that exchange.
- **RS benchmark:** Defaults to NSE:NIFTY. Change to NSE:NIFTYBANK for banking stocks or your preferred index.
- **ATR Stop:** The red line below price is a **trailing stop suggestion**, not a fixed level. It moves with volatility.

---

## 📱 Setting Up Alerts

1. Right-click the indicator on your chart → **"Add Alert"**
2. Select the condition:
   - `BUY A` / `BUY B` / `BUY C` / `STRONG BUY`
   - `SELL X` / `SELL Y` / `SELL Z`
3. Choose notification: Push notification, Email, or Webhook
4. Alerts include the ticker name automatically in the message

---

*Built for disciplined swing and position traders who follow price, momentum, and fundamentals.*
*Methodology: Minervini Trend Template + Mansfield RS + Weinstein Stage Analysis + Volume Price Analysis*
