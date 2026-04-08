/**
 * INDIA SWING SCANNER — REPORT DATA MODULE
 * Pre-seeded weekly flash report data for week of 7 April 2026
 * In a production system, this would be fetched from live APIs.
 */

const REPORT_DATA = {
  generatedAt: "07 Apr 2026, 08:30",
  reportType: "Monday Pre-Market",
  capitalBase: 1000000, // ₹10 Lakhs
  maxRiskPct: 0.02, // 2% per trade

  /* ══════════════════════════════════════════════
     TAB 1 — MARKET SNAPSHOT
  ══════════════════════════════════════════════ */
  market: {
    indices: [
      { label: "Nifty 50", value: "22,513", change: "-1.2%", pts: "-279", trend: "bearish", weekly: "-2.1%", sub: "Apr 4 Close" },
      { label: "Nifty Bank", value: "47,890", change: "+0.4%", pts: "+188", trend: "neutral", weekly: "-0.8%", sub: "Apr 4 Close" },
      { label: "Sensex", value: "74,248", change: "-1.1%", pts: "-836", trend: "bearish", weekly: "-2.0%", sub: "Apr 4 Close" },
      { label: "Nifty Midcap 100", value: "49,215", change: "-0.8%", pts: "-394", trend: "bearish", weekly: "-3.2%", sub: "Apr 4 Close" },
    ],
    fii: { label: "FII Net Flow (Week)", value: "-₹6,234 Cr", type: "sell", note: "Net sellers; tariff uncertainty driving exit" },
    dii: { label: "DII Net Flow (Week)", value: "+₹8,412 Cr", type: "buy", note: "Strong domestic buying; SIPs & mutual fund inflows" },
    bias: "Cautiously Bullish",
    biasClass: "neutral",
    biasNote: "DIIs supporting market at lower levels. Global headwinds (Trump tariff 26% on India) creating near-term volatility. Nifty holding key 22,000 support.",
    topSectors: ["PSU Banks", "FMCG", "Pharma"],
    events: [
      { date: "08 Apr", tag: "data", tagClass: "blue",    desc: "RBI MPC Meeting begins — Rate decision 9 Apr" },
      { date: "09 Apr", tag: "policy", tagClass: "red",   desc: "RBI Policy Rate decision — Market expects 25bps cut to 6.0%" },
      { date: "10 Apr", tag: "data", tagClass: "amber",   desc: "India CPI Inflation data release (Mar 2026)" },
      { date: "11 Apr", tag: "results", tagClass: "green",desc: "Q4 FY26 results season begins — TCS, Infosys, HDFC Bank" },
      { date: "14 Apr", tag: "holiday", tagClass: "blue", desc: "Dr. Ambedkar Jayanti — NSE/BSE Market Holiday" },
    ]
  },

  /* ══════════════════════════════════════════════
     TAB 2 — TOP SWING SETUPS
  ══════════════════════════════════════════════ */
  setups: [
    {
      rank: 1,
      name: "SBI (State Bank of India)",
      ticker: "SBIN",
      cmp: "₹793.40",
      marketCap: "Mid-Large Cap · ₹7.08L Cr",
      setupType: "breakout",
      setupLabel: "Technical Breakout",
      technical: {
        rsi: { value: 58, label: "58.2", interpretation: "Momentum building — not yet overbought" },
        macd: { signal: "bullish", label: "Bullish crossover", detail: "MACD line crossed above signal on Apr 3" },
        dma: { above20: true, above50: true, above200: true, label: "Price > 20 DMA > 50 DMA ✅ Full Bull" },
        volume: { status: "surge", label: "1.8x avg volume on breakout candle", detail: "Avg 20D: ₹1,240Cr/day" },
        support: "₹770",
        resistance: "₹825",
      },
      fundamental: {
        pe: "9.8x",
        sectorPe: "11.2x",
        de: "15.8x (Banking — Normal)",
        promoterHolding: "57.4%",
        promoterTrend: "Stable",
        salesGrowth: "+14.2%",
        profitGrowth: "+18.6%",
        lastQtr: "Q3 FY26",
      },
      trigger: "PSU Banks rallying on expectation of RBI rate cut (9 Apr). SBI showing relative strength with DII accumulation visible in block deals. Net Interest Margin expansion story intact.",
      trade: {
        entryLow: 790, entryHigh: 798,
        sl: 768, slPct: "2.8%",
        t1: 825, t1Pct: "+3.9%",
        t2: 858, t2Pct: "+8.0%",
        rrRatio: "1:2.5",
        rrReward: 75,
        positionAmount: "₹1.60L",
        shares: "200 shares",
      },
      news: { clean: true, summary: "No major negative news. RBI rate cut expectation bullish for banking sector." },
      chartLink: "https://www.tradingview.com/chart/?symbol=NSE%3ASBIN",
      sources: "NSE India, Screener.in, Moneycontrol",
    },
    {
      rank: 2,
      name: "Sun Pharma",
      ticker: "SUNPHARMA",
      cmp: "₹1,672.85",
      marketCap: "Large Cap · ₹4.01L Cr",
      setupType: "sector",
      setupLabel: "Sector Rotation Play",
      technical: {
        rsi: { value: 54, label: "54.3", interpretation: "Mid-range — room to run higher" },
        macd: { signal: "bullish", label: "Bullish momentum", detail: "MACD histogram expanding positively" },
        dma: { above20: true, above50: true, above200: true, label: "Price > 20 DMA > 50 DMA ✅ Full Bull" },
        volume: { status: "normal", label: "1.2x avg volume — steady accumulation", detail: "Avg 20D: ₹420Cr/day" },
        support: "₹1,620",
        resistance: "₹1,740",
      },
      fundamental: {
        pe: "38.2x",
        sectorPe: "32.5x",
        de: "0.04x (Near Debt-Free)",
        promoterHolding: "54.8%",
        promoterTrend: "Stable",
        salesGrowth: "+11.8%",
        profitGrowth: "+22.4%",
        lastQtr: "Q3 FY26",
      },
      trigger: "Pharma sector receiving defensive capital flows as global trade uncertainty escalates (US tariff on Indian pharma at 0% so far — strategic advantage). Sun Pharma's US generics pipeline strong with 27 ANDA approvals pending.",
      trade: {
        entryLow: 1660, entryHigh: 1680,
        sl: 1615, slPct: "3.1%",
        t1: 1740, t1Pct: "+4.2%",
        t2: 1820, t2Pct: "+8.9%",
        rrRatio: "1:2.4",
        rrReward: 72,
        positionAmount: "₹1.68L",
        shares: "100 shares",
      },
      news: { clean: true, summary: "Pharma exempt from Trump tariff 2.0 wave — structurally positive for entire sector." },
      chartLink: "https://www.tradingview.com/chart/?symbol=NSE%3ASUNPHARMA",
      sources: "NSE India, Screener.in, Economic Times",
    },
    {
      rank: 3,
      name: "ITC Limited",
      ticker: "ITC",
      cmp: "₹408.15",
      marketCap: "Large Cap · ₹5.13L Cr",
      setupType: "reversion",
      setupLabel: "Mean Reversion",
      technical: {
        rsi: { value: 38, label: "38.4", interpretation: "Oversold — bounce likely from support" },
        macd: { signal: "bullish", label: "Bullish divergence forming", detail: "Price making lower lows but MACD higher lows — positive divergence" },
        dma: { above20: false, above50: false, above200: true, label: "Price < 20/50 DMA but > 200 DMA — oversold in uptrend" },
        volume: { status: "dry", label: "Volume drying at support — buyers absorbing", detail: "50% below 20D avg — distribution done" },
        support: "₹395",
        resistance: "₹435",
      },
      fundamental: {
        pe: "27.4x",
        sectorPe: "41.2x (FMCG)",
        de: "0.0x (Zero Debt)",
        promoterHolding: "0% (Widely Held)",
        promoterTrend: "N/A",
        salesGrowth: "+9.2%",
        profitGrowth: "+13.1%",
        lastQtr: "Q3 FY26",
      },
      trigger: "FMCG defensive play. ITC trading at significant discount to FMCG sector PE. Hotels segment spun off, unlocking shareholder value. RSI <40 with volume dry-up near 200 DMA support — classic mean reversion setup. Strong dividend yield ~3.2%.",
      trade: {
        entryLow: 400, entryHigh: 410,
        sl: 389, slPct: "2.7%",
        t1: 435, t1Pct: "+6.3%",
        t2: 455, t2Pct: "+11.3%",
        rrRatio: "1:3.1",
        rrReward: 84,
        positionAmount: "₹2.00L",
        shares: "490 shares",
      },
      news: { clean: true, summary: "No negative news. Hotels demerger positively received. ITC Hotels listed at premium." },
      chartLink: "https://www.tradingview.com/chart/?symbol=NSE%3AITC",
      sources: "NSE India, Screener.in, Moneycontrol",
    },
    {
      rank: 4,
      name: "Bajaj Finance",
      ticker: "BAJFINANCE",
      cmp: "₹8,412.50",
      marketCap: "Large Cap · ₹5.22L Cr",
      setupType: "earnings",
      setupLabel: "Earnings Momentum",
      technical: {
        rsi: { value: 62, label: "62.1", interpretation: "Mild overbought — use strict SL" },
        macd: { signal: "bullish", label: "Strong bullish — post-results momentum", detail: "MACD sharply above signal line post Q3 beat" },
        dma: { above20: true, above50: true, above200: true, label: "Price > 20 DMA > 50 DMA ✅ Full Bull" },
        volume: { status: "surge", label: "2.1x avg post-results — strong institutional interest", detail: "Block deals: ₹890Cr in last 3 sessions" },
        support: "₹8,100",
        resistance: "₹8,800",
      },
      fundamental: {
        pe: "32.5x",
        sectorPe: "28.4x (NBFC)",
        de: "5.2x (Within NBFC norms)",
        promoterHolding: "52.7%",
        promoterTrend: "Stable",
        salesGrowth: "+26.3% (NII)",
        profitGrowth: "+22.8%",
        lastQtr: "Q3 FY26",
      },
      trigger: "Bajaj Finance delivered strong Q3 FY26 results — AUM growth 27% YoY, asset quality stable (GNPA 1.12%). RBI rate cut expected to compress cost of funds, expanding NIMs. Institutional upgrades from JP Morgan, Nomura post-results.",
      trade: {
        entryLow: 8350, entryHigh: 8450,
        sl: 8090, slPct: "3.1%",
        t1: 8800, t1Pct: "+4.9%",
        t2: 9200, t2Pct: "+9.4%",
        rrRatio: "1:2.4",
        rrReward: 72,
        positionAmount: "₹1.68L",
        shares: "20 shares",
      },
      news: { clean: false, summary: "Strong Q3 results beat. Broker upgrades from JP Morgan (+BUY, TP ₹9,800), Nomura (+BUY, TP ₹9,400). RBI rate cut catalyst ahead." },
      chartLink: "https://www.tradingview.com/chart/?symbol=NSE%3ABAJFINANCE",
      sources: "NSE India, Screener.in, ET Markets",
    },
  ],

  /* ══════════════════════════════════════════════
     TAB 3 — WATCHLIST
  ══════════════════════════════════════════════ */
  watchlist: [
    { name: "Reliance Industries", ticker: "RELIANCE", cmp: "₹1,238", watchLevel: "₹1,200 support", trigger: "Await breakout above ₹1,270 with volume", readiness: "warm" },
    { name: "Tata Motors", ticker: "TATAMOTORS", cmp: "₹626", watchLevel: "₹600 support zone", trigger: "JLR update + EV sales data needed", readiness: "cool" },
    { name: "Infosys", ticker: "INFY", cmp: "₹1,486", watchLevel: "Q4 results on Apr 11", trigger: "Buy on results dip <₹1,450 if guidance positive", readiness: "hot" },
    { name: "HDFC Bank", ticker: "HDFCBANK", cmp: "₹1,748", watchLevel: "₹1,700 demand zone", trigger: "Await rate cut clarity; watch Q4 margins", readiness: "warm" },
    { name: "Adani Ports", ticker: "ADANIPORTS", cmp: "₹1,094", watchLevel: "₹1,060 support", trigger: "Wait for FII reentry confirmation", readiness: "cool" },
    { name: "Divi's Laboratories", ticker: "DIVISLAB", cmp: "₹5,386", watchLevel: "₹5,100 demand zone", trigger: "Pharma sector momentum + RSI correction to <45", readiness: "warm" },
    { name: "Zomato (Eternal)", ticker: "ZOMATO", cmp: "₹218", watchLevel: "₹200 psychological support", trigger: "Watch Blinkit GMV update; RSI approaching 40", readiness: "hot" },
    { name: "LTIMindtree", ticker: "LTIM", cmp: "₹4,892", watchLevel: "Q4 results catalyst", trigger: "IT sector recovery + deal wins needed", readiness: "cool" },
  ],

  /* ══════════════════════════════════════════════
     TAB 4 — SECTOR HEATMAP
  ══════════════════════════════════════════════ */
  sectors: [
    { name: "Pharma", index: "Nifty Pharma", change: "+2.8%", vol: "FII buying", hm: "hm-strong-bull", rank: 1 },
    { name: "PSU Banks", index: "Nifty PSU Bank", change: "+2.1%", vol: "DII accumulation", hm: "hm-strong-bull", rank: 2 },
    { name: "FMCG", index: "Nifty FMCG", change: "+1.4%", vol: "Defensive flows", hm: "hm-bull", rank: 3 },
    { name: "Healthcare", index: "Nifty Healthcare", change: "+1.1%", vol: "Moderate", hm: "hm-bull", rank: 4 },
    { name: "Private Banks", index: "Nifty Bank", change: "-0.6%", vol: "Mixed", hm: "hm-flat", rank: 5 },
    { name: "Auto", index: "Nifty Auto", change: "-0.9%", vol: "Weak", hm: "hm-flat", rank: 6 },
    { name: "Energy", index: "Nifty Energy", change: "-1.2%", vol: "FII selling", hm: "hm-slight-bear", rank: 7 },
    { name: "IT / Tech", index: "Nifty IT", change: "-2.4%", vol: "High selling", hm: "hm-bear", rank: 8 },
    { name: "Metal & Mining", index: "Nifty Metal", change: "-3.1%", vol: "China demand fears", hm: "hm-strong-bear", rank: 9 },
    { name: "Realty", index: "Nifty Realty", change: "-3.6%", vol: "Institutional exit", hm: "hm-strong-bear", rank: 10 },
    { name: "Media", index: "Nifty Media", change: "+0.3%", vol: "Low", hm: "hm-slight-bull", rank: 11 },
    { name: "Infra", index: "Nifty Infra", change: "-1.8%", vol: "Budget concerns", hm: "hm-bear", rank: 12 },
  ],

  /* ══════════════════════════════════════════════
     TAB 5 — RISK DASHBOARD
  ══════════════════════════════════════════════ */
  risk: {
    vix: { value: "14.2", label: "India VIX", status: "MODERATE", class: "medium" },
    niftySupport: ["22,000 (Psychological)", "21,700 (200 DMA)", "21,350 (Demand Zone)"],
    niftyResistance: ["22,800 (Previous High)", "23,200 (All-time High Zone)", "23,500 (Supply Zone)"],
    niftyCurrent: "22,513",
    overallRisk: { level: "Medium", class: "medium" },
    macro: [
      { indicator: "Crude Oil (Brent)", value: "$71.8/bbl", impact: "Positive (below ₹6,000 comfort zone)", impactClass: "bullish" },
      { indicator: "USD / INR", value: "₹83.82", impact: "Neutral (stable range 83–84)", impactClass: "neutral" },
      { indicator: "US 10Y Yield", value: "4.38%", impact: "Neutral — watch Fed signals", impactClass: "neutral" },
      { indicator: "Gold (MCX)", value: "₹91,400/10g", impact: "Negative for equities — safe haven demand up", impactClass: "bearish" },
      { indicator: "DXY (Dollar Index)", value: "103.2", impact: "Neutral — moderate dollar strength", impactClass: "neutral" },
      { indicator: "China Shanghai Comp", value: "-2.4% WoW", impact: "Negative — tariff war impact on metals", impactClass: "bearish" },
    ],
    upcomingEvents: [
      "RBI Policy Rate Decision — 9 April 2026 (Expect 25bps cut)",
      "India CPI Inflation — 10 April 2026",
      "TCS Q4 FY26 Results — 11 April 2026",
      "US Core CPI Data — 10 April 2026 (Key for Fed signals)",
      "Market Holiday — 14 April (Ambedkar Jayanti)",
    ]
  }
};
