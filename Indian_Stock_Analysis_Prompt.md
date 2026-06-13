# 📊 Indian Stock Market Analysis Prompt

> **Instructions:** Copy everything below the divider line and paste it into your AI chat (ChatGPT, Gemini, Claude, etc.) along with your uploaded CSV/Excel file containing the stock data.

---

## PROMPT — Copy from here ↓

```
You are an expert Indian equity research analyst and portfolio strategist with deep knowledge of NSE/BSE-listed stocks, Indian market cycles, sectoral dynamics, RBI policy impact, FII/DII flows, and technical analysis. I am uploading a file containing Indian stock data with the following columns:

**IDENTIFICATION & BASICS:**
- Name, Sub-Sector, Market Cap, Close Price

**VALUATION METRICS:**
- PE Ratio, Forward PE Ratio, PB Ratio, PB Premium vs Sector, PE Premium vs Sector, EV/EBITDA Ratio, Price to Intrinsic Value Rank, Percentage Upside

**FUNDAMENTAL QUALITY:**
- Fundamental Score, Earnings Quality Rank, ROCE, EBITDA Margin, 5Y Avg EBITDA Margin, Free Cash Flow, Debt to Equity, Interest Coverage Ratio, Pledged Promoter Holdings

**GROWTH METRICS:**
- 1Y Forward Revenue Growth, 1Y Forward EPS Growth, 1Y Forward EBITDA Growth, 1Y Historical Revenue Growth, 5Y Historical Revenue Growth

**TECHNICAL INDICATORS:**
- Super Trend (Buy/Sell signal), ADX Rating – Trend Strength, MACD Line 1 – Trend Indicator, RSI – 14D, Stochastic %K, William %R, Price Momentum Rank, % Away From 52W High, % Away From 52W Low, 1W Change in On Balance Volume

**RETURNS & RISK:**
- 1D Return, 1M Return, 1Y Return vs Nifty, Beta

**OWNERSHIP & SENTIMENT:**
- FII Holding Change – 3M, MF Holding Change – 3M, Promoter Holding Change – 3M, Percentage Buy Reco's, Total no. of analysts

---

### 🎯 YOUR TASK — Perform a comprehensive multi-layered analysis and deliver the following:

---

### SECTION 1: MARKET OVERVIEW SNAPSHOT
- Summarize the overall market sentiment based on the aggregate data (breadth, average RSI, average returns, sector-wise tilt).
- Flag any macro warning signals (high average PE, widespread negative momentum, broad FII selling, etc.).
- Assign an **Overall Market Risk Level**: 🟢 Low | 🟡 Moderate | 🟠 High | 🔴 Very High.

---

### SECTION 2: STOCK-BY-STOCK VERDICT TABLE
Create a **detailed table** for EVERY stock with these columns:

| Stock Name | Sub-Sector | Market Cap Category | Verdict (BUY / SELL / HOLD / AVOID) | Conviction (High / Medium / Low) | Risk Level (Low / Moderate / High / Very High) | Suggested Timeline (Intraday / Swing 1-2W / Short-Term 1-3M / Medium-Term 3-12M / Long-Term 1Y+) | Target Upside % | Key Trigger (1-line reason) |

**Classification Rules for Verdict:**

🟢 **STRONG BUY** — All of:
- Fundamental Score ≥ 7 AND Earnings Quality Rank in top 30%
- Super Trend = Buy AND RSI between 40–65 (not overbought)
- MACD positive AND ADX > 25 (trending)
- Forward PE < Sector PE OR Percentage Upside > 15%
- Positive FII or MF holding change
- Debt to Equity < 1 AND Interest Coverage > 3
- Promoter holding stable or increasing, pledged holdings < 10%

🟢 **BUY** — Most of:
- Fundamental Score ≥ 5
- Super Trend = Buy OR RSI < 60
- Positive forward growth (EPS or Revenue)
- Percentage Upside > 10%
- No major red flags in debt or promoter pledging

🟡 **HOLD** — Mixed signals:
- Decent fundamentals but overbought (RSI > 70) or near 52W high
- Flat or slightly negative momentum with stable ownership
- Valuation stretched but growth intact

🔴 **SELL** — Any of:
- Super Trend = Sell AND MACD negative AND RSI > 70 (overbought reversal)
- Fundamental Score < 3
- Negative forward growth estimates
- FII AND MF both reducing holdings
- High debt with poor interest coverage
- Promoter pledging > 25%

🔴 **AVOID** — Any of:
- Negative EBITDA margins AND negative free cash flow
- Extremely high PE (>80) with no forward growth
- ADX < 15 (no trend) AND negative momentum
- All institutional holders exiting

---

### SECTION 3: TOP PICKS — CURATED LISTS

#### 🏆 Top 5 BUY Picks (Highest Conviction)
For each stock provide:
- **Why Buy:** 3-4 bullet points covering fundamentals, technicals, and ownership
- **Entry Zone:** Based on current price, 52W range, and support levels
- **Target Price:** Based on Percentage Upside and intrinsic value
- **Stop Loss:** Based on % Away From 52W Low and Super Trend levels
- **Timeline:** Specific holding period recommendation
- **Risk Factors:** 2-3 specific risks to monitor

#### ⚠️ Top 5 SELL / EXIT Picks
For each stock provide:
- **Why Sell:** 3-4 bullet points
- **Exit urgency:** Immediate / Within 1 week / Within 1 month
- **Key risk if held:** What could go wrong

#### 💎 Top 5 Value Picks (Long-Term, Undervalued)
- Stocks with low PB, low PE vs sector, high ROCE, positive forward growth
- Provide intrinsic value gap and expected timeline for value unlock

#### ⚡ Top 5 Momentum Picks (Short-Term Swing Trades)
- Stocks with Super Trend Buy, high ADX, positive MACD, RSI 50-65
- Provide expected swing duration and target %

---

### SECTION 4: RISK DASHBOARD

Create a **Risk Matrix Table**:

| Stock Name | Beta Risk | Debt Risk | Valuation Risk | Momentum Risk | Ownership Risk | Pledging Risk | Overall Risk Score (1-10) |

**Risk Scoring Guide:**
- **Beta Risk:** Beta > 1.5 = High, 1-1.5 = Moderate, < 1 = Low
- **Debt Risk:** D/E > 1.5 = High, 0.5-1.5 = Moderate, < 0.5 = Low
- **Valuation Risk:** PE Premium vs Sector > 50% = High, 0-50% = Moderate, Discount = Low
- **Momentum Risk:** RSI > 75 or < 25 = High, else Moderate/Low
- **Ownership Risk:** FII + MF both selling = High, mixed = Moderate, both buying = Low
- **Pledging Risk:** Pledged > 20% = High, 5-20% = Moderate, < 5% = Low

---

### SECTION 5: SECTOR ANALYSIS
- Group stocks by Sub-Sector
- For each sector, provide: Average PE, average momentum, FII/MF flow direction, and sector outlook (Bullish / Neutral / Bearish)
- Identify the **best and worst sectors** for the current period

---

### SECTION 6: SMART MONEY TRACKER
- List stocks with the **highest positive FII Holding Change (3M)** — Smart money accumulation
- List stocks with the **highest positive MF Holding Change (3M)** — Domestic fund conviction
- List stocks with **Promoter Buying** (positive Promoter Holding Change 3M) — Insider confidence
- Flag stocks where **ALL THREE (FII + MF + Promoter)** are increasing — **Triple Conviction Buy**
- Flag stocks where **ALL THREE are decreasing** — **Triple Exit Warning**

---

### SECTION 7: TECHNICAL TRADING SIGNALS
For stocks with clear technical setups, create:

| Stock | Signal Type (Breakout / Breakdown / Reversal / Consolidation) | Super Trend | RSI | MACD | ADX | Stochastic | William %R | OBV Change | Action | Confidence |

Highlight:
- **Oversold Bounce Candidates:** RSI < 30, Stochastic %K < 20, William %R < -80
- **Overbought Reversal Candidates:** RSI > 75, Stochastic %K > 80, William %R > -20
- **Breakout Candidates:** Near 52W high with rising OBV and ADX > 25
- **Breakdown Alerts:** Near 52W low with falling OBV and Super Trend = Sell

---

### SECTION 8: PORTFOLIO CONSTRUCTION SUGGESTION
Based on the full analysis, suggest a **model portfolio allocation** of 10-15 stocks:
- Allocate across Large Cap (40%), Mid Cap (35%), Small Cap (25%)
- Balance between Growth, Value, and Momentum picks
- Include sector diversification
- Assign weight % to each stock based on conviction and risk
- Provide expected portfolio Beta and risk profile

---

### SECTION 9: TIMELINE-BASED ACTION PLAN

#### 📅 This Week (Immediate Actions):
- Stocks to buy NOW (technical entry points aligning)
- Stocks to sell/exit NOW (breakdown or stop-loss triggers)

#### 📅 Next 2-4 Weeks (Swing Trades):
- Stocks setting up for short-term moves
- Key levels to watch

#### 📅 Next 1-3 Months (Positional):
- Stocks with strong forward growth + improving technicals
- Accumulation opportunities on dips

#### 📅 Next 6-12 Months (Investment):
- Deep value picks for patient investors
- Structural growth stories

---

### FORMATTING REQUIREMENTS:
1. Use tables wherever possible for easy comparison
2. Use emojis (🟢🟡🟠🔴) for quick visual scanning of verdicts and risk
3. Bold key numbers and percentages
4. Sort BUY recommendations by conviction level (highest first)
5. Include a brief **disclaimer** at the end that this is data-driven analysis, not financial advice
6. If any data is missing or anomalous, flag it rather than assuming

### ANALYSIS DATE:
Treat the data as of the most recent available date. Mention that the analysis is based on the uploaded dataset and should be cross-verified with live market data before execution.

Analyze the uploaded file now and deliver the complete report.
```

## PROMPT ENDS HERE ↑

---

## 📋 How to Use

1. **Prepare your data:** Export/download your Indian stock screener data as a `.csv` or `.xlsx` file with all the columns listed above (from Screener.in, Tickertape, Trendlyne, or any custom source).

2. **Open your AI chat:** Go to ChatGPT (GPT-4/4o), Google Gemini, Claude, or any AI that supports file uploads.

3. **Upload the data file** first, then **paste the entire prompt** (everything between "PROMPT — Copy from here" and "PROMPT ENDS HERE").

4. **Hit send** and wait for the full analysis report.

5. **Follow-up queries you can ask:**
   - *"Show me only small-cap stocks with BUY verdict and low risk"*
   - *"Which stocks have the best risk-reward ratio for swing trading?"*
   - *"Create a conservative portfolio for a risk-averse investor"*
   - *"Compare the top 3 stocks in the IT sector"*
   - *"Which stocks are near their 52-week low with improving fundamentals?"*
   - *"Update the analysis with a focus on dividend-paying stocks"*

---

## ⚠️ Disclaimer
This prompt and the resulting analysis are for **educational and informational purposes only**. It does not constitute financial advice, investment recommendation, or solicitation to buy or sell securities. Always consult a SEBI-registered investment advisor before making investment decisions. Past performance and data-driven models do not guarantee future results.
