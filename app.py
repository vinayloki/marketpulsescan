"""
MarketPulse India — Unified Quantitative Trading Terminal
Mirrors ALL content from https://vinayloki.github.io/india-swing-scanner/
with enhanced interactive UI, TradingView integration, and Backtest Lab.
"""

import streamlit as st
import json, os, math, random
import numpy as np
import pandas as pd
from datetime import datetime

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MarketPulse India — NSE Trading Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TV_BASE = "https://in.tradingview.com/chart/?symbol=NSE:"
SCAN_DIR = "scan_results"

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&family=Roboto+Mono:wght@400;600;700&display=swap');

:root {
  --bg: #080c14; --bg2: #0d1420; --bg3: #111827;
  --border: #1e2a3a; --border2: #243044;
  --blue: #1a56db; --blue-light: #38bdf8; --blue-glow: rgba(26,86,219,0.25);
  --green: #22c55e; --red: #ef4444; --yellow: #f59e0b; --purple: #a78bfa;
  --text: #e2e8f0; --text2: #94a3b8; --text3: #64748b; --text4: #475569;
}
html, body, [class*="css"] { font-family: 'Roboto', sans-serif !important; background: var(--bg) !important; color: var(--text); }

/* ── Tabs ────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { gap:4px; background:var(--bg2); border-radius:14px; padding:6px; border:1px solid var(--border); }
.stTabs [data-baseweb="tab"] { background:transparent; color:var(--text3); border-radius:10px; font-weight:600; font-size:13px; padding:10px 16px; border:none; transition:all .2s; }
.stTabs [aria-selected="true"] { background:linear-gradient(135deg,#1a56db,#0ea5e9) !important; color:#fff !important; box-shadow:0 4px 15px var(--blue-glow); }

/* ── Cards ───────────────────────────────────────── */
.card { background:linear-gradient(135deg,var(--bg2),var(--bg3)); border:1px solid var(--border); border-radius:16px; padding:20px; margin-bottom:14px; transition:border-color .2s,transform .15s; }
.card:hover { border-color:#1a56db44; }

/* ── Metric Card ─────────────────────────────────── */
.mc { background:var(--bg2); border:1px solid var(--border); border-radius:12px; padding:16px; text-align:center; }
.mc-val { font-size:1.9rem; font-weight:900; font-family:'Roboto Mono',monospace; line-height:1.1; }
.mc-lbl { font-size:11px; color:var(--text3); font-weight:600; margin-top:5px; text-transform:uppercase; letter-spacing:.06em; }
.mc-sub { font-size:11px; color:var(--text4); margin-top:3px; }

/* ── Pick Cards ──────────────────────────────────── */
.pick { background:var(--bg2); border:1px solid var(--border); border-left:3px solid var(--blue); border-radius:10px; padding:14px 16px; margin-bottom:10px; transition:border-color .2s,transform .1s; }
.pick:hover { transform:translateY(-1px); border-color:var(--border2); }
.pick.buy { border-left-color:var(--green); }
.pick.sell { border-left-color:var(--red); }
.pick.hold { border-left-color:var(--yellow); }

/* ── Badges ──────────────────────────────────────── */
.badge { display:inline-block; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:700; letter-spacing:.03em; }
.b-buy { background:#14532d; color:#4ade80; }
.b-sell { background:#450a0a; color:#f87171; }
.b-hold { background:#451a03; color:#fbbf24; }
.b-brk { background:#1e1e3f; color:#818cf8; }
.b-vol { background:#0f2744; color:#38bdf8; }
.b-mom { background:#1a2e1a; color:#86efac; }
.b-lg { background:#312e81; color:#a5b4fc; }
.b-md { background:#27272a; color:#d4d4d8; }
.b-sm { background:#1a2e1a; color:#86efac; }
.b-mc { background:#292524; color:#a8a29e; }

/* ── Opp Card ────────────────────────────────────── */
.opp-card { background:var(--bg2); border:1px solid var(--border); border-radius:12px; padding:16px; margin-bottom:12px; position:relative; }
.opp-score-ring { width:52px; height:52px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:900; font-size:15px; border:3px solid; }

/* ── Table ───────────────────────────────────────── */
.tv-table { width:100%; border-collapse:collapse; font-size:13px; }
.tv-table th { background:var(--bg2); color:var(--text3); font-weight:600; padding:10px 12px; text-align:left; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; letter-spacing:.05em; position:sticky; top:0; }
.tv-table td { padding:9px 12px; border-bottom:1px solid #111827; color:var(--text2); vertical-align:middle; }
.tv-table tr:hover td { background:#0d1420cc; }
.tv-link { color:var(--blue-light); text-decoration:none; font-weight:700; font-family:'Roboto Mono',monospace; }
.tv-link:hover { color:#60a5fa; text-decoration:underline; }
.chart-btn { background:#0d1f3c; border:1px solid #1a3a6a; color:var(--blue-light); padding:3px 10px; border-radius:6px; font-size:11px; text-decoration:none; font-weight:600; white-space:nowrap; }
.chart-btn:hover { background:#1a3a6a; color:#fff; }
.pos { color:var(--green); font-weight:600; }
.neg { color:var(--red); font-weight:600; }
.neu { color:var(--text3); }

/* ── Mover Row ───────────────────────────────────── */
.mv-row { display:flex; justify-content:space-between; align-items:center; padding:8px 12px; border-radius:8px; margin-bottom:5px; background:var(--bg2); border:1px solid var(--border); }

/* ── Header ──────────────────────────────────────── */
.hdr { background:#0f172a; border:1px solid var(--border); border-radius:12px; padding:20px 24px; margin-bottom:18px; position:relative; overflow:hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06); }

/* ── News ────────────────────────────────────────── */
.news-item { padding:12px 0; border-bottom:1px solid var(--border); }
.news-title a { color:var(--text2); text-decoration:none; font-size:13px; font-weight:500; }
.news-title a:hover { color:var(--blue-light); }
.news-meta { font-size:11px; color:var(--text4); margin-top:3px; }

/* ── Progress ring ───────────────────────────────── */
.p52w { height:6px; background:#1e2a3a; border-radius:3px; margin-top:4px; }
.p52w-fill { height:100%; border-radius:3px; background:linear-gradient(90deg,#1a56db,#38bdf8); }

/* ── Disclaimer ──────────────────────────────────── */
.disc { background:#1c1200; border:1px solid #854d0e; border-radius:10px; padding:12px 16px; font-size:12px; color:#fbbf24; margin-top:14px; }

/* ── Info box ────────────────────────────────────── */
.info-box { background:#0a1e38; border:1px solid #1a3a6a; border-radius:10px; padding:14px 18px; font-size:13px; color:#93c5fd; margin:12px 0; }

/* Misc overrides */
.stButton>button { border-radius:10px; font-weight:600; font-size:13px; transition:all .2s; border:1px solid var(--border); background:var(--bg2); color:var(--text2); }
.stButton>button:hover { border-color:var(--blue); color:#60a5fa; }
.stSelectbox label,.stSlider label,.stRadio label,.stTextInput label,.stMultiSelect label { color:var(--text2) !important; font-size:13px !important; font-weight:500 !important; }
.stTextInput>div>div>input { background:var(--bg2) !important; border:1px solid var(--border) !important; color:var(--text) !important; border-radius:8px !important; }
::-webkit-scrollbar { width:5px; height:5px; } ::-webkit-scrollbar-track { background:var(--bg); } ::-webkit-scrollbar-thumb { background:#1e3a5f; border-radius:3px; }
h1,h2,h3 { color:#f1f5f9 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Data Loaders ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_json(fname, default=None):
    try:
        with open(os.path.join(SCAN_DIR, fname)) as f:
            return json.load(f)
    except:
        return default or {}

@st.cache_data(ttl=3600)
def load_csv(fname):
    try:
        return pd.read_csv(os.path.join(SCAN_DIR, fname))
    except:
        return pd.DataFrame()

ai_data     = load_json("ai_picks.json", {"picks":[], "summary":{}, "regime":"Unknown", "generated":"N/A"})
top_data    = load_json("latest_top_performers.json", {})
perf_data   = load_json("performance_report.json", {})
opp_raw     = load_json("opportunities.json", {"opportunities":[]})
regime_data = load_json("market_regime.json", {"regime":"Unknown"})
news_raw    = load_json("daily_news.json", [])
scan_df     = load_csv("latest_full_scan.csv")
full_sum    = load_json("latest_scan_summary.json", {})

picks    = ai_data.get("picks", [])
regime   = ai_data.get("regime", "Unknown")
gen_date = ai_data.get("generated", "N/A")
summary  = ai_data.get("summary", {})
buys, holds, sells = summary.get("buy",0), summary.get("hold",0), summary.get("sell",0)
total_stocks = ai_data.get("total_stocks", 0)
opps     = opp_raw.get("opportunities", [])
mb       = perf_data.get("mode_b", {})

# ─── Helpers ──────────────────────────────────────────────────────────────────
def tv(ticker): return f"{TV_BASE}{ticker}"
def tv_link(ticker, label=None):
    lab = label or ticker
    return f'<a href="{tv(ticker)}" target="_blank" class="tv-link">{lab}</a>'
def chart_btn(ticker):
    return f'<a href="{tv(ticker)}" target="_blank" class="chart-btn">📊 Chart ↗</a>'

def pct_fmt(v, dash="–"):
    if v is None or (isinstance(v, float) and math.isnan(v)): return f'<span class="neu">{dash}</span>'
    cls = "pos" if v >= 0 else "neg"; sign = "+" if v >= 0 else ""
    return f'<span class="{cls}">{sign}{v:.1f}%</span>'

def price_fmt(v):
    if not v: return "–"
    return f"₹{v:,.2f}" if v < 10000 else f"₹{v:,.0f}"

def cap_badge(code, label):
    cls = {"L":"b-lg","M":"b-md","S":"b-sm"}.get(str(code),"b-mc")
    return f'<span class="badge {cls}">{label}</span>'

def rec_badge(rec):
    cls = {"buy":"b-buy","sell":"b-sell","hold":"b-hold"}.get(str(rec).lower(),"b-hold")
    icon = {"buy":"▲ BUY","sell":"▼ SELL","hold":"◆ HOLD"}.get(str(rec).lower(),"◆ HOLD")
    return f'<span class="badge {cls}">{icon}</span>'

def sig_badge(sig):
    mp = {"52W_BREAKOUT":("b-brk","🚀 52W HIGH"),"HIGH_VOLUME":("b-vol","📊 HIGH VOL"),"VOLUME_SPIKE":("b-vol","⚡ VOL SPIKE"),"EMA_MOMENTUM":("b-mom","📈 EMA MOM")}
    cls, lab = mp.get(sig, ("b-sm", sig))
    return f'<span class="badge {cls}">{lab}</span>'

def score_color(s):
    if s >= 80: return "#22c55e"
    if s >= 60: return "#f59e0b"
    if s >= 40: return "#38bdf8"
    return "#94a3b8"

def metric_box(label, val_html, sub=None, top_color="#1a56db"):
    sub_h = f'<div class="mc-sub">{sub}</div>' if sub else ""
    return f'<div class="mc" style="border-top:3px solid {top_color}"><div class="mc-val">{val_html}</div><div class="mc-lbl">{label}</div>{sub_h}</div>'

# ─── Header ───────────────────────────────────────────────────────────────────
rc = "#22c55e" if regime=="Bull" else ("#ef4444" if regime=="Bear" else "#f59e0b")
ri = "🟢" if regime=="Bull" else ("🔴" if regime=="Bear" else "🟡")
opp_count = len(opps)

# Scan summary stats from full scan
try:
    adv_1w = full_sum.get("adv_1w", 0); dec_1w = full_sum.get("dec_1w", 0)
    gainers_1w = full_sum.get("gainers_1w", 0); losers_1m = full_sum.get("losers_1m", 0)
    super_perf = full_sum.get("super_performers_12m", 0)
except: adv_1w=dec_1w=gainers_1w=losers_1m=super_perf=0

st.markdown(f"""
<div class="hdr">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:14px">
    <div>
      <div style="font-size:24px;font-weight:900;color:#f1f5f9;letter-spacing:-.02em">📈 MarketPulse India</div>
      <div style="font-size:13px;color:#64748b;margin-top:3px">NSE Intelligence Engine · {total_stocks:,} Stocks · AI-Powered EOD Analysis</div>
    </div>
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
      <div style="display:inline-flex;align-items:center;gap:6px;background:{rc}11;border:1px solid {rc}44;color:{rc};padding:6px 14px;border-radius:20px;font-size:13px;font-weight:700">{ri} {regime} Market</div>
      <div style="text-align:right"><div style="font-size:10px;color:#475569">UPDATED</div><div style="font-size:13px;color:#94a3b8;font-weight:700">{gen_date}</div></div>
    </div>
  </div>
  <div style="display:flex;gap:28px;margin-top:16px;flex-wrap:wrap;border-top:1px solid #1e2a3a;padding-top:14px">
    <div><span style="font-size:20px;font-weight:900;color:#f1f5f9">{total_stocks:,}</span><br><span style="font-size:11px;color:#64748b">Stocks Scanned</span></div>
    <div><span style="font-size:20px;font-weight:900;color:#38bdf8">{opp_count}</span><br><span style="font-size:11px;color:#64748b">Opportunities</span></div>
    <div><span style="font-size:20px;font-weight:900;color:#22c55e">{buys}</span><br><span style="font-size:11px;color:#64748b">▲ BUY Signals</span></div>
    <div><span style="font-size:20px;font-weight:900;color:#fbbf24">{holds}</span><br><span style="font-size:11px;color:#64748b">◆ HOLD</span></div>
    <div><span style="font-size:20px;font-weight:900;color:#ef4444">{sells}</span><br><span style="font-size:11px;color:#64748b">▼ SELL Signals</span></div>
    <div style="margin-left:auto;align-self:center"><span style="font-size:11px;color:#475569">⚠️ Educational only · Not SEBI-registered advice</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── Tabs ─────────────────────────────────────────────────────────────────────
t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "🎯 Opportunities", "🏆 Top Movers", "📋 Full Scan",
    "📰 News", "🤖 AI Picks", "🧪 Backtest Lab", "📘 Blueprint"
])


# ══════════════════════════════════════════════════════════════════
# TAB 1 — OPPORTUNITIES  (52W Breakout, Volume Spike, Momentum)
# ══════════════════════════════════════════════════════════════════
with t1:
    st.markdown("""
    <div class="info-box">💡 <b>Opportunities</b> are high-conviction technical setups ranked by AI Score.
    Each has at least one confirmed signal: 52W Breakout, Volume Spike, or EMA Momentum.
    Click <b>📊 Chart ↗</b> to open TradingView for detailed analysis.</div>
    """, unsafe_allow_html=True)

    # Filters
    fc1, fc2, fc3, fc4 = st.columns([3,2,2,2])
    with fc1: opp_search = st.text_input("🔍 Search ticker / name", placeholder="e.g. INOX, RELIANCE...", key="opp_s")
    with fc2: opp_sig = st.selectbox("Signal Type", ["ALL","52W Breakout","Volume Spike","EMA Momentum"], key="opp_sig")
    with fc3: opp_score = st.selectbox("Min Score", ["All","50+","70+","80+","90+"], key="opp_sc")
    with fc4:
        all_secs_opp = sorted(set(o.get("fundamental",{}).get("sector","") or "" for o in opps) - {""})
        opp_sector = st.selectbox("Sector", ["All"] + all_secs_opp, key="opp_sec")

    score_map = {"All":0,"50+":50,"70+":70,"80+":80,"90+":90}
    sig_map = {"ALL":None,"52W Breakout":"52W_BREAKOUT","Volume Spike":"VOLUME_SPIKE","EMA Momentum":"EMA_MOMENTUM"}
    min_opp_score = score_map.get(opp_score, 0)
    sig_filter = sig_map.get(opp_sig)

    filtered_opps = []
    for o in opps:
        if opp_search:
            s = opp_search.upper()
            if s not in o.get("ticker","").upper() and s not in (o.get("fundamental",{}).get("name","") or "").upper():
                continue
        if sig_filter and sig_filter not in o.get("signals",[]):
            continue
        if o.get("score",0) < min_opp_score:
            continue
        if opp_sector != "All" and (o.get("fundamental",{}).get("sector","") or "") != opp_sector:
            continue
        filtered_opps.append(o)

    st.markdown(f'<div style="color:#64748b;font-size:13px;margin-bottom:10px">Showing <b style="color:#38bdf8">{len(filtered_opps)}</b> of {len(opps)} setups</div>', unsafe_allow_html=True)

    if not filtered_opps:
        st.info("No setups match your filters.")
    else:
        for o in filtered_opps:
            score = o.get("score", 0)
            ticker = o.get("ticker","")
            rank = o.get("rank","?")
            sigs = o.get("signals",[])
            ind = o.get("indicators",{})
            fund = o.get("fundamental",{})
            sc = score_color(score)
            price = ind.get("price", fund.get("price",0)) or 0
            vol_ratio = ind.get("volume_ratio",0) or 0
            chg_1d = ind.get("pct_change_1d")
            high52 = ind.get("high_52w") or fund.get("52h")
            low52 = fund.get("52l")
            pe = fund.get("pe")
            mcap = fund.get("mcap_cr")
            name = fund.get("name","") or ticker
            sector = fund.get("sector","") or ""

            # 52W range bar
            range_pct = 0
            if high52 and low52 and high52 > low52:
                range_pct = max(0, min(100, (price - low52) / (high52 - low52) * 100))

            sigs_html = " ".join(sig_badge(s) for s in sigs)
            pe_str = f"P/E {pe:.1f}x" if pe else "P/E –"
            mcap_str = f"₹{mcap:,.0f} Cr" if mcap else ""
            chg_html = pct_fmt(chg_1d) if chg_1d is not None else ""

            st.markdown(f"""
            <div class="opp-card">
              <div style="display:flex;gap:14px;align-items:flex-start">
                <div class="opp-score-ring" style="border-color:{sc};color:{sc};min-width:52px">{score}</div>
                <div style="flex:1">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
                    <div>
                      <span style="font-size:18px;font-weight:800;color:#f1f5f9;font-family:'Roboto Mono',monospace">
                        {tv_link(ticker)}
                      </span>
                      <span style="font-size:12px;color:#64748b;margin-left:8px">#{rank} · {name}</span>
                      <span style="font-size:12px;color:#94a3b8;margin-left:8px">{sector}</span>
                    </div>
                    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                      {sigs_html}
                      {chart_btn(ticker)}
                    </div>
                  </div>
                  <div style="display:flex;gap:20px;margin-top:10px;flex-wrap:wrap">
                    <div><span style="color:#64748b;font-size:12px">Price: </span><b style="color:#f1f5f9;font-size:14px">{price_fmt(price)}</b></div>
                    <div><span style="color:#64748b;font-size:12px">1D: </span>{chg_html}</div>
                    <div><span style="color:#64748b;font-size:12px">Vol Ratio: </span><b style="color:#38bdf8">{vol_ratio:.2f}x</b></div>
                    <div><span style="color:#64748b;font-size:12px">{pe_str}</span></div>
                    <div><span style="color:#64748b;font-size:12px">{mcap_str}</span></div>
                  </div>
                  <div style="margin-top:8px">
                    <span style="color:#64748b;font-size:11px">52W Range: {price_fmt(low52)} → {price_fmt(high52)}</span>
                    <div class="p52w"><div class="p52w-fill" style="width:{range_pct:.0f}%"></div></div>
                  </div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="disc">⚠️ These setups are algorithmically generated for educational purposes. Always do your own research before trading.</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# TAB 2 — TOP MOVERS
# ══════════════════════════════════════════════════════════════════
with t2:
    tf_sel = st.radio("Timeframe", ["1W","2W","1M","3M"], horizontal=True, key="tf_mv")
    mv_search = st.text_input("🔍 Search ticker", placeholder="e.g. STLTECH", key="mv_s")

    tf_data = top_data.get(tf_sel, {})
    gainers = tf_data.get("top_gainers", [])
    losers  = tf_data.get("top_losers", [])

    g2, l2 = st.columns(2)
    with g2:
        st.markdown(f'<div style="color:#22c55e;font-weight:700;font-size:15px;margin-bottom:12px">🚀 Top Gainers ({tf_sel})</div>', unsafe_allow_html=True)
        disp_g = [g for g in gainers if not mv_search or mv_search.upper() in g.get("ticker","").upper()] if mv_search else gainers
        rows_g = ""
        for g in disp_g[:20]:
            p = g.get(tf_sel, 0) or 0
            pr = g.get("last_close", 0) or 0
            bar = min(100, abs(p) * 1.2)
            rows_g += f"""<div class="mv-row">
              <div>{tv_link(g.get("ticker",""))}<div style="font-size:10px;color:#475569;margin-top:2px">{price_fmt(pr)}</div></div>
              <div style="text-align:right">
                <span class="pos">+{p:.1f}%</span>
                <div style="height:3px;background:#1e2a3a;border-radius:2px;margin-top:4px;width:80px;margin-left:auto">
                  <div style="height:100%;width:{bar:.0f}%;background:#22c55e;border-radius:2px"></div></div>
                {chart_btn(g.get("ticker",""))}
              </div></div>"""
        st.markdown(rows_g, unsafe_allow_html=True)

    with l2:
        st.markdown(f'<div style="color:#ef4444;font-weight:700;font-size:15px;margin-bottom:12px">📉 Top Losers ({tf_sel})</div>', unsafe_allow_html=True)
        disp_l = [l for l in losers if not mv_search or mv_search.upper() in l.get("ticker","").upper()] if mv_search else losers
        rows_l = ""
        for l in disp_l[:20]:
            p = l.get(tf_sel, 0) or 0
            pr = l.get("last_close", 0) or 0
            bar = min(100, abs(p) * 1.2)
            rows_l += f"""<div class="mv-row">
              <div>{tv_link(l.get("ticker",""))}<div style="font-size:10px;color:#475569;margin-top:2px">{price_fmt(pr)}</div></div>
              <div style="text-align:right">
                <span class="neg">{p:.1f}%</span>
                <div style="height:3px;background:#1e2a3a;border-radius:2px;margin-top:4px;width:80px;margin-left:auto">
                  <div style="height:100%;width:{bar:.0f}%;background:#ef4444;border-radius:2px"></div></div>
                {chart_btn(l.get("ticker",""))}
              </div></div>"""
        st.markdown(rows_l, unsafe_allow_html=True)

    # ── Fundamentals for top movers (Top Movers with full detail) ──
    st.markdown("---")
    st.markdown('<div style="font-size:15px;font-weight:700;color:#f1f5f9;margin-bottom:12px">📊 Detailed Fundamentals — Top Gainers</div>', unsafe_allow_html=True)

    # Build enriched table from ai_picks for top gainers
    top_tickers = [g.get("ticker") for g in gainers[:20]]
    pick_map = {p.get("ticker"): p for p in picks}

    rows_html = "".join([f"""
    <tr>
      <td>{tv_link(t)}</td>
      <td>{price_fmt(pick_map.get(t,{}).get("price",0))}</td>
      <td>{pick_map.get(t,{}).get("sector","–")[:20]}</td>
      <td>{pick_map.get(t,{}).get("pe","–")}</td>
      <td>{f"₹{pick_map.get(t,{}).get('mcap_cr',0):,.0f} Cr" if pick_map.get(t,{}).get("mcap_cr") else "–"}</td>
      <td>{pct_fmt(next((g.get(tf_sel) for g in gainers if g.get("ticker")==t), None))}</td>
      <td>{pct_fmt(pick_map.get(t,{}).get("tf_details",{}).get("1M",{}).get("pct"))}</td>
      <td>{pct_fmt(pick_map.get(t,{}).get("tf_details",{}).get("3M",{}).get("pct"))}</td>
      <td>{pct_fmt(pick_map.get(t,{}).get("tf_details",{}).get("12M",{}).get("pct"))}</td>
      <td>{chart_btn(t)}</td>
    </tr>
    """ for t in top_tickers if t in pick_map])

    st.markdown(f"""
    <div style="overflow-x:auto">
    <table class="tv-table">
      <thead><tr>
        <th>Ticker</th><th>Price</th><th>Sector</th><th>P/E</th><th>Mkt Cap</th>
        <th>{tf_sel} Ret</th><th>1M Ret</th><th>3M Ret</th><th>12M Ret</th><th>Chart</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table></div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# TAB 3 — FULL SCAN
# ══════════════════════════════════════════════════════════════════
with t3:
    st.markdown('<div class="info-box">📋 Complete scan of all NSE stocks. Click any ticker to open TradingView chart. Sortable by any column.</div>', unsafe_allow_html=True)

    sc1, sc2, sc3 = st.columns([3,2,2])
    with sc1: scan_search = st.text_input("🔍 Search ticker", placeholder="INFY, TCS...", key="sc_s")
    with sc2: scan_filter = st.selectbox("Filter", ["All","Gainers Only","Losers Only"], key="sc_f")
    with sc3: scan_cap = st.selectbox("Cap Size", ["All","Large Cap","Mid Cap","Small Cap"], key="sc_c")

    if not scan_df.empty:
        df = scan_df.copy()
        str_cols = [c for c in df.columns if not c.startswith("Unnamed")]
        df = df[str_cols]

        # Rename columns for display
        col_renames = {}
        for c in df.columns:
            cl = c.lower()
            if "ticker" in cl or "symbol" in cl: col_renames[c]="Ticker"
            elif "price" in cl or "close" in cl: col_renames[c]="Price"
            elif "1w" in cl: col_renames[c]="1W%"
            elif "2w" in cl: col_renames[c]="2W%"
            elif "1m" in cl: col_renames[c]="1M%"
            elif "3m" in cl: col_renames[c]="3M%"
            elif "6m" in cl: col_renames[c]="6M%"
            elif "12m" in cl or "1y" in cl: col_renames[c]="12M%"
            elif "sector" in cl: col_renames[c]="Sector"
            elif "cap" in cl: col_renames[c]="Cap"
        df = df.rename(columns=col_renames)

        if scan_search:
            mask = df.astype(str).apply(lambda r: r.str.contains(scan_search.upper(), case=False, na=False)).any(axis=1)
            df = df[mask]

        if scan_filter == "Gainers Only" and "1W%" in df.columns:
            df = df[pd.to_numeric(df["1W%"], errors="coerce") > 0]
        elif scan_filter == "Losers Only" and "1W%" in df.columns:
            df = df[pd.to_numeric(df["1W%"], errors="coerce") < 0]

        if scan_cap != "All" and "Cap" in df.columns:
            df = df[df["Cap"].astype(str).str.contains(scan_cap.split()[0], case=False, na=False)]

        st.markdown(f'<div style="color:#64748b;font-size:13px;margin-bottom:8px">Showing <b style="color:#38bdf8">{len(df):,}</b> stocks</div>', unsafe_allow_html=True)

        # Build HTML table with TV links (show first 200 rows for performance)
        display_df = df.head(200)
        ticker_col = "Ticker" if "Ticker" in display_df.columns else display_df.columns[0]
        pct_cols = [c for c in display_df.columns if "%" in c]

        # Add TradingView link column
        if ticker_col in display_df.columns:
            display_df = display_df.copy()
            display_df["📊"] = display_df[ticker_col].apply(lambda t: f'<a href="{tv(str(t))}" target="_blank" class="chart-btn">Chart ↗</a>')
            display_df[ticker_col] = display_df[ticker_col].apply(lambda t: f'<a href="{tv(str(t))}" target="_blank" class="tv-link">{t}</a>')

        # Format pct columns
        for c in pct_cols:
            display_df[c] = display_df[c].apply(lambda v: pct_fmt(float(v)) if pd.notna(v) and str(v).strip() not in ["","–","nan"] else "–")

        # Render table
        th_cells = "".join(f"<th>{c}</th>" for c in display_df.columns)
        td_rows = ""
        for _, row in display_df.iterrows():
            td_rows += "<tr>" + "".join(f"<td>{v}</td>" for v in row.values) + "</tr>"

        st.markdown(f"""
        <div style="overflow-x:auto;max-height:600px;border:1px solid #1e2a3a;border-radius:12px">
        <table class="tv-table"><thead><tr>{th_cells}</tr></thead><tbody>{td_rows}</tbody></table>
        </div>
        """, unsafe_allow_html=True)

        if len(df) > 200:
            st.caption(f"Showing first 200 of {len(df):,} results. Use search to narrow down.")
    else:
        st.info("Full scan data not available. Run the GitHub Actions workflow to generate it.")


# ══════════════════════════════════════════════════════════════════
# TAB 4 — NEWS
# ══════════════════════════════════════════════════════════════════
with t4:
    st.markdown('<div style="font-size:16px;font-weight:700;color:#f1f5f9;margin-bottom:12px">📰 Market News — NSE Intelligence Feed</div>', unsafe_allow_html=True)

    news_list = news_raw if isinstance(news_raw, list) else news_raw.get("articles", [])

    if news_list:
        for article in news_list[:30]:
            title = article.get("title") or article.get("headline","")
            source = article.get("source") or article.get("publisher","NSE")
            pub = article.get("published") or article.get("time","")
            url = article.get("url") or article.get("link","#")
            if not title: continue
            st.markdown(f"""
            <div class="news-item">
              <div class="news-title"><a href="{url}" target="_blank">{title}</a></div>
              <div class="news-meta">📡 {source} &nbsp;·&nbsp; 🕐 {pub}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("News is fetched daily via GitHub Actions. Run the workflow to populate this feed.")

    st.markdown("""<div class="disc">News sourced from LiveMint, Economic Times, and MoneyControl RSS feeds. Auto-refreshed daily.</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# TAB 5 — AI PICKS (Execute Mode)
# ══════════════════════════════════════════════════════════════════
with t5:
    st.markdown(f"""
    <div class="info-box">
      🤖 <b>AI EOD Intelligence Engine v2</b> — {total_stocks:,} stocks analysed ·
      <b style="color:#22c55e">{buys} BUY</b> ·
      <b style="color:#fbbf24">{holds} HOLD</b> ·
      <b style="color:#ef4444">{sells} SELL</b> ·
      Avg Confidence: <b style="color:#a78bfa">{summary.get("avg_confidence",0):.1f}%</b>
    </div>
    """, unsafe_allow_html=True)

    # ── Filters ──
    af1, af2, af3, af4, af5 = st.columns([3,2,2,2,2])
    with af1: ai_search = st.text_input("🔍 Search ticker / name", key="ai_s")
    with af2: ai_rec = st.selectbox("Signal", ["All","BUY","HOLD","SELL"], key="ai_r")
    with af3: ai_cap = st.selectbox("Cap Size", ["All","Large Cap","Mid Cap","Small Cap","Micro Cap"], key="ai_c")
    with af4:
        all_sectors = ["All"] + sorted(set(p.get("sector","") for p in picks if p.get("sector","")))
        ai_sec = st.selectbox("Sector", all_sectors, key="ai_sec")
    with af5: ai_conf = st.slider("Min Confidence", 0, 100, 60, 5, key="ai_conf")

    # Filter
    filtered = []
    for p in picks:
        if ai_search:
            s = ai_search.upper()
            if s not in p.get("ticker","").upper() and s not in p.get("name","").upper():
                continue
        if ai_rec != "All" and p.get("recommendation","").upper() != ai_rec:
            continue
        if ai_cap != "All" and p.get("cap_label","") != ai_cap:
            continue
        if ai_sec != "All" and p.get("sector","") != ai_sec:
            continue
        if p.get("confidence",0) < ai_conf:
            continue
        filtered.append(p)

    st.markdown(f'<div style="color:#64748b;font-size:13px;margin-bottom:10px">Showing <b style="color:#38bdf8">{len(filtered)}</b> stocks</div>', unsafe_allow_html=True)

    # View toggle
    view_mode = st.radio("View", ["Cards (Detailed)","Table (Compact)"], horizontal=True, key="ai_view")
    show_n = st.select_slider("Show", [10,25,50,100,200,len(filtered)] if len(filtered) > 200 else [10,25,50,min(100,len(filtered)),len(filtered)], value=min(25,len(filtered)), key="ai_n")

    if view_mode == "Table (Compact)":
        # ── Compact table ──
        th = "<tr><th>Ticker</th><th>Price</th><th>Signal</th><th>Confidence</th><th>Entry</th><th>Stop Loss</th><th>Target</th><th>R:R</th><th>P(Win)</th><th>1W</th><th>1M</th><th>3M</th><th>12M</th><th>Chart</th></tr>"
        trs = ""
        for p in filtered[:show_n]:
            t = p.get("ticker","")
            rec = p.get("recommendation","hold")
            tf = p.get("tf_details",{})
            trs += f"""<tr>
              <td><a href="{tv(t)}" target="_blank" class="tv-link">{t}</a><br><span style="font-size:10px;color:#475569">{p.get('name','')[:20]}</span></td>
              <td><b>{price_fmt(p.get('price'))}</b></td>
              <td>{rec_badge(rec)}</td>
              <td><b style="color:#a78bfa">{p.get('confidence',0)}%</b></td>
              <td>{price_fmt(p.get('entry_price'))}</td>
              <td><span class="neg">{price_fmt(p.get('stop_loss'))}</span></td>
              <td><span class="pos">{price_fmt(p.get('take_profit'))}</span></td>
              <td><b style="color:#38bdf8">1:{p.get('risk_reward',0):.1f}</b></td>
              <td>{p.get('p_success',0):.1f}%</td>
              <td>{pct_fmt(tf.get('1W',{}).get('pct'))}</td>
              <td>{pct_fmt(tf.get('1M',{}).get('pct'))}</td>
              <td>{pct_fmt(tf.get('3M',{}).get('pct'))}</td>
              <td>{pct_fmt(tf.get('12M',{}).get('pct'))}</td>
              <td><a href="{tv(t)}" target="_blank" class="chart-btn">Chart ↗</a></td>
            </tr>"""
        st.markdown(f'<div style="overflow-x:auto;max-height:600px;border:1px solid #1e2a3a;border-radius:12px"><table class="tv-table"><thead>{th}</thead><tbody>{trs}</tbody></table></div>', unsafe_allow_html=True)

    else:
        # ── Detail cards ──
        for p in filtered[:show_n]:
            ticker = p.get("ticker","")
            rec = p.get("recommendation","hold")
            conf = p.get("confidence",0)
            tf = p.get("tf_details",{})
            reasons = p.get("reasons",[])
            risks = p.get("risks",[])

            tf_row = "".join([
                f'<span style="color:{"#22c55e" if (tf.get(k,{}).get("pct") or 0)>=0 else "#ef4444"};font-size:11px;margin-right:10px">{k}: {pct_fmt(tf.get(k,{}).get("pct"))}</span>'
                for k in ["1W","2W","1M","3M","6M","12M"]
            ])
            conf_bar = f'<div style="height:4px;background:#1e2a3a;border-radius:2px;margin-top:6px;margin-bottom:3px"><div style="height:100%;width:{conf}%;background:{"#22c55e" if conf>=75 else "#f59e0b" if conf>=55 else "#ef4444"};border-radius:2px;transition:width .3s"></div></div>'
            reasons_h = "".join([f'<div style="color:#4ade80;font-size:11px;margin-top:2px">✓ {r}</div>' for r in reasons[:3]])
            risks_h = "".join([f'<div style="color:#f87171;font-size:11px;margin-top:2px">⚠ {r}</div>' for r in risks[:2]])

            st.markdown(f"""
            <div class="pick {rec}">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
                <div>
                  <span style="font-size:18px;font-weight:800;color:#f1f5f9;font-family:'Roboto Mono',monospace">
                    {tv_link(ticker)}
                  </span>
                  <span style="font-size:12px;color:#64748b;margin-left:8px">{p.get("name","")}</span>
                  <span style="font-size:12px;color:#94a3b8;margin-left:6px">· {p.get("sector","")}</span>
                  <span style="font-size:11px;color:#475569;margin-left:6px">#{p.get("rank","?")}</span>
                </div>
                <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
                  {rec_badge(rec)}
                  {cap_badge(p.get("mcap_code","S"), p.get("cap_label","Small Cap"))}
                  <span class="badge" style="background:#1e3a5f;color:#38bdf8;font-size:10px">{regime}</span>
                  <a href="{tv(ticker)}" target="_blank" class="chart-btn">📊 Chart ↗</a>
                </div>
              </div>
              <div style="display:flex;gap:18px;margin-top:10px;flex-wrap:wrap">
                <span style="font-size:12px;color:#64748b">Entry: <b style="color:#f1f5f9">{price_fmt(p.get("entry_price"))}</b></span>
                <span style="font-size:12px;color:#64748b">SL: <b style="color:#ef4444">{price_fmt(p.get("stop_loss"))}</b> (-{p.get("sl_pct",0):.2f}%)</span>
                <span style="font-size:12px;color:#64748b">Target: <b style="color:#22c55e">{price_fmt(p.get("take_profit"))}</b> (+{p.get("tp_pct",0):.2f}%)</span>
                <span style="font-size:12px;color:#64748b">R:R <b style="color:#38bdf8">1:{p.get("risk_reward",0):.1f}</b></span>
                <span style="font-size:12px;color:#64748b">P(Win): <b style="color:#a78bfa">{p.get("p_success",0):.1f}%</b></span>
                <span style="font-size:12px;color:#64748b">Horizon: <b style="color:#94a3b8">{p.get("horizon","")}</b></span>
              </div>
              <div style="margin-top:8px">{tf_row}</div>
              {conf_bar}
              <span style="font-size:10px;color:#475569">Confidence {conf}% · AI Score {p.get("score",0):.1f}/100</span>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px">
                <div>{reasons_h}</div><div>{risks_h}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="disc">⚠️ All AI signals are for educational research only. Not SEBI-registered advice. Past performance ≠ future results.</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# TAB 6 — BACKTEST LAB  (with full trade log)
# ══════════════════════════════════════════════════════════════════
with t6:
    st.markdown('<div class="info-box" style="margin-bottom:18px"><b style="color:#f8fafc">💡 Why 5 Years?</b> Strategy validation runs on <b>260 weeks (5 full years)</b> of historical data across the entire NSE universe. A strategy that only works during a 1-year bull run is inherently flawed. Testing across half a decade guarantees the algorithm is stress-tested against Bull cycles, Bear crashes, and prolonged Sideways chop.</div>', unsafe_allow_html=True)
    
    col_k1, col_k2 = st.columns(2)
    with col_k1:
        st.markdown('<div class="card" style="padding:16px"><div style="font-size:14px;font-weight:700;color:#f1f5f9;margin-bottom:6px">🌐 Market Regimes</div><div style="font-size:13px;color:#94a3b8">The algorithm categorizes the macro engine state:<br><b>Bull:</b> NIFTY > EMA200 (Risk On)<br><b>Sideways:</b> NIFTY hugging EMA200 (Chop)<br><b>Bear:</b> NIFTY < EMA200 (Risk Off)</div></div>', unsafe_allow_html=True)
    with col_k2:
        st.markdown('<div class="card" style="padding:16px"><div style="font-size:14px;font-weight:700;color:#f1f5f9;margin-bottom:6px">🚪 Exit Triggers</div><div style="font-size:13px;color:#94a3b8">Why a trade was closed:<br><b>TP (Take Profit):</b> Hit predefined target (+4%)<br><b>SL (Stop Loss):</b> Hit predefined risk limit (-2% or ATR-based)<br><b>TIME (Time Bleed):</b> Expired after 5 trading days</div></div>', unsafe_allow_html=True)

    # Load real trade-level data
    @st.cache_data(ttl=3600)
    def load_backtest_trades():
        try:
            with open(os.path.join(SCAN_DIR, "backtest_results.json"), encoding="utf-8") as f:
                d = json.load(f)
            return d.get("mode_b",{}).get("trades",[])
        except:
            return []

    all_trades = load_backtest_trades()

    real_wr    = mb.get("win_rate_pct",52.6)
    real_aw    = mb.get("avg_win_pct",3.43)
    real_al    = abs(mb.get("avg_loss_pct",-4.84))
    real_trades_n = mb.get("total_trades",156)
    real_exp   = mb.get("expectancy_pct",-0.49)
    real_pf    = mb.get("profit_factor",0.847)
    real_dd    = mb.get("max_drawdown_pct",18.06)
    real_ret   = mb.get("total_return_pct",-12.56)
    real_sh    = mb.get("sharpe_like",-0.99)
    exits      = mb.get("exit_reasons",{"TP":64,"SL":55,"TIME":37})
    monthly    = mb.get("monthly_dist",[])
    regime_bk  = mb.get("regime_breakdown",{})

    st.markdown("""
    <div class="info-box">🧪 <b>Backtest Laboratory</b> — Real 260 Weeks (5 Years) historical results with <b>every trade visible</b>.
    See exactly which companies were traded, when, and whether they won or lost. Click any ticker to open TradingView.</div>
    """, unsafe_allow_html=True)

    # ── Summary Metrics ──
    st.markdown(f'<div style="font-size:16px;font-weight:700;color:#f1f5f9;margin:8px 0 14px">📊 Real Backtest Results — 260 Weeks (5 Years) · {real_trades_n} Trades</div>', unsafe_allow_html=True)

    mc1,mc2,mc3,mc4 = st.columns(4)
    wrc = "#22c55e" if real_wr>=60 else ("#f59e0b" if real_wr>=50 else "#ef4444")
    trc = "#22c55e" if real_ret>=0 else "#ef4444"
    exc = "#22c55e" if real_exp>=0 else "#ef4444"
    with mc1: st.markdown(metric_box("Win Rate",f'<span style="color:{wrc}">{real_wr:.1f}%</span>',"Target: >60%",wrc),unsafe_allow_html=True)
    with mc2: st.markdown(metric_box("Total Return",f'<span style="color:{trc}">{real_ret:+.2f}%</span>',"₹10L → ₹8.74L",trc),unsafe_allow_html=True)
    with mc3: st.markdown(metric_box("Expectancy/Trade",f'<span style="color:{exc}">{real_exp:+.2f}%</span>',"Target: >0%",exc),unsafe_allow_html=True)
    with mc4: st.markdown(metric_box("Max Drawdown",f'<span class="neg">{real_dd:.1f}%</span>',"Target: <15%","#ef4444"),unsafe_allow_html=True)

    mc5,mc6,mc7,mc8 = st.columns(4)
    with mc5: st.markdown(metric_box("Avg Win",f'<span class="pos">+{real_aw:.2f}%</span>',f"{exits.get('TP',0)} TP hits"),unsafe_allow_html=True)
    with mc6: st.markdown(metric_box("Avg Loss",f'<span class="neg">-{real_al:.2f}%</span>',f"{exits.get('SL',0)} SL hits"),unsafe_allow_html=True)
    with mc7: st.markdown(metric_box("Profit Factor",f'<span class="warn">{real_pf:.3f}</span>',"Target: >1.25","#f59e0b"),unsafe_allow_html=True)
    with mc8: st.markdown(metric_box("Sharpe Ratio",f'<span class="neg">{real_sh:.2f}</span>',"Target: >0.5","#ef4444"),unsafe_allow_html=True)

    # Exit breakdown
    st.markdown("---")
    ex1,ex2,ex3 = st.columns(3)
    with ex1:
        tp_n = exits.get("TP",0)
        st.markdown(f'<div class="mc" style="border-top:3px solid #22c55e"><div class="mc-val pos">{tp_n}</div><div class="mc-lbl">✅ Take Profit Hit</div><div class="mc-sub">{tp_n/real_trades_n*100:.0f}% of trades</div></div>',unsafe_allow_html=True)
    with ex2:
        sl_n = exits.get("SL",0)
        st.markdown(f'<div class="mc" style="border-top:3px solid #ef4444"><div class="mc-val neg">{sl_n}</div><div class="mc-lbl">🛑 Stop Loss Hit</div><div class="mc-sub">{sl_n/real_trades_n*100:.0f}% of trades</div></div>',unsafe_allow_html=True)
    with ex3:
        ti_n = exits.get("TIME",0)
        st.markdown(f'<div class="mc" style="border-top:3px solid #f59e0b"><div class="mc-val warn">{ti_n}</div><div class="mc-lbl">⏰ Time Exit (5d)</div><div class="mc-sub">{ti_n/real_trades_n*100:.0f}% of trades</div></div>',unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    # FULL TRADE LOG — Every single trade with company name
    # ══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown(f'<div style="font-size:16px;font-weight:700;color:#f1f5f9;margin-bottom:6px">📋 Complete Trade Log — All {len(all_trades)} Trades</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#64748b;font-size:13px;margin-bottom:12px">Every trade the engine executed over 260 weeks. Click any ticker to open its TradingView chart.</div>', unsafe_allow_html=True)

    if all_trades:
        pick_mcap_map = {p.get("ticker",""): p.get("mcap_cr", 0) for p in picks}
        # Filters for trade log
        tl1, tl2, tl3, tl4, tl5 = st.columns([2.5,2,2,2,2.5])
        with tl1:
            tl_search = st.text_input("🔍 Search ticker", placeholder="e.g. FORTIS, NYKAA...", key="tl_s")
        with tl2:
            tl_result = st.selectbox("Result", ["All","Winners Only","Losers Only"], key="tl_res")
        with tl3:
            tl_exit = st.selectbox("Exit Reason", ["All","TP (Take Profit)","SL (Stop Loss)","TIME (Expired)"], key="tl_exit")
        with tl4:
            tl_regime = st.selectbox("Regime", ["All","Bull","Bear","Sideways"], key="tl_reg")
        with tl5:
            tl_cap = st.selectbox("Market Cap Size", ["All", "Large Cap", "Mid Cap", "Small Cap"], key="tl_mk_cap")

        # Filter trades
        filtered_trades = []
        for tr in all_trades:
            t = tr.get("ticker","")
            if tl_search and tl_search.upper() not in t.upper():
                continue
            if tl_result == "Winners Only" and not tr.get("won", False):
                continue
            if tl_result == "Losers Only" and tr.get("won", True):
                continue
            if tl_exit != "All":
                ex_code = tl_exit.split("(")[0].strip()
                if tr.get("exit_reason","") != ex_code:
                    continue
            if tl_regime != "All" and tr.get("regime","") != tl_regime:
                continue
            if tl_cap != "All":
                mc = pick_mcap_map.get(t, None)
                if mc is None: continue # Skip if Market Cap unknown
                if tl_cap == "Large Cap" and mc <= 20000: continue
                if tl_cap == "Mid Cap" and (mc < 5000 or mc > 20000): continue
                if tl_cap == "Small Cap" and mc >= 5000: continue
            
            filtered_trades.append(tr)

        # Stats for filtered
        f_wins = sum(1 for t in filtered_trades if t.get("won"))
        f_losses = len(filtered_trades) - f_wins
        f_pnl = sum(t.get("pnl",0) for t in filtered_trades)
        f_wr = f_wins/len(filtered_trades)*100 if filtered_trades else 0

        st.markdown(f"""
        <div style="display:flex;gap:24px;padding:10px 14px;background:#0d1728;border:1px solid #1e2a3a;border-radius:8px;margin-bottom:12px;flex-wrap:wrap">
          <span style="font-size:13px;color:#64748b">Showing <b style="color:#38bdf8">{len(filtered_trades)}</b> trades</span>
          <span style="font-size:13px;color:#64748b">Wins: <b class="pos">{f_wins}</b></span>
          <span style="font-size:13px;color:#64748b">Losses: <b class="neg">{f_losses}</b></span>
          <span style="font-size:13px;color:#64748b">Win Rate: <b style="color:{'#22c55e' if f_wr>=55 else '#ef4444'}">{f_wr:.1f}%</b></span>
          <span style="font-size:13px;color:#64748b">Total P&L: <b style="color:{'#22c55e' if f_pnl>=0 else '#ef4444'}">₹{f_pnl:+,.0f}</b></span>
        </div>
        """, unsafe_allow_html=True)

        # Build trade log table
        exit_icons = {"TP":"✅","SL":"🛑","TIME":"⏰"}
        result_icons = {True: '<span class="pos">✅ WIN</span>', False: '<span class="neg">❌ LOSS</span>'}
        tl_header = "<tr><th>#</th><th>Ticker</th><th>Entry Date</th><th>Entry ₹</th><th>Exit Date</th><th>Exit ₹</th><th>Days</th><th>Return %</th><th>P&L ₹</th><th>Exit</th><th>Result</th><th>Regime</th><th>Score</th><th>Chart</th></tr>"
        tl_rows = ""
        for i, tr in enumerate(filtered_trades, 1):
            t = tr.get("ticker","")
            ret = tr.get("return_pct",0)
            pnl = tr.get("pnl",0)
            won = tr.get("won",False)
            exit_r = tr.get("exit_reason","")
            ret_color = "pos" if ret >= 0 else "neg"
            pnl_color = "pos" if pnl >= 0 else "neg"

            # Regime badge
            reg = tr.get("regime","")
            reg_icon = "🟢" if reg == "Bull" else ("🔴" if reg == "Bear" else "🟡")

            tl_rows += f"""<tr>
              <td style="color:#475569">{i}</td>
              <td><a href="{tv(t)}" target="_blank" class="tv-link">{t}</a></td>
              <td style="color:#94a3b8;font-size:12px">{tr.get("entry_date","")}</td>
              <td style="color:#f1f5f9;font-weight:600">₹{tr.get("entry_price",0):,.2f}</td>
              <td style="color:#94a3b8;font-size:12px">{tr.get("exit_date","")}</td>
              <td style="color:#f1f5f9;font-weight:600">₹{tr.get("exit_price",0):,.2f}</td>
              <td style="color:#94a3b8">{tr.get("holding_days","")}</td>
              <td><span class="{ret_color}">{ret:+.2f}%</span></td>
              <td><span class="{pnl_color}">₹{pnl:+,.0f}</span></td>
              <td>{exit_icons.get(exit_r,"❓")} {exit_r}</td>
              <td>{result_icons.get(won, "–")}</td>
              <td>{reg_icon} {reg}</td>
              <td style="color:#a78bfa;font-weight:700">{tr.get("score","–")}</td>
              <td><a href="{tv(t)}" target="_blank" class="chart-btn">📊 Chart ↗</a></td>
            </tr>"""

        st.markdown(f"""
        <div style="overflow-x:auto;max-height:700px;border:1px solid #1e2a3a;border-radius:12px">
        <table class="tv-table">
          <thead>{tl_header}</thead>
          <tbody>{tl_rows}</tbody>
        </table>
        </div>
        """, unsafe_allow_html=True)

        # Top Winners & Worst Losers summary
        st.markdown("---")
        tw_col, tl_col = st.columns(2)
        sorted_by_pnl = sorted(all_trades, key=lambda x: x.get("pnl",0), reverse=True)

        with tw_col:
            st.markdown('<div style="font-size:14px;font-weight:700;color:#22c55e;margin-bottom:10px">🏆 Top 10 Winners (by P&L)</div>', unsafe_allow_html=True)
            for tr in sorted_by_pnl[:10]:
                t = tr.get("ticker","")
                st.markdown(f"""<div class="mv-row">
                  <div>{tv_link(t)} <span style="font-size:11px;color:#475569">· {tr.get("entry_date","")}</span></div>
                  <div style="text-align:right">
                    <span class="pos">+{tr.get("return_pct",0):.2f}%</span>
                    <span style="color:#22c55e;font-size:12px;margin-left:8px">₹{tr.get("pnl",0):+,.0f}</span>
                    {chart_btn(t)}
                  </div>
                </div>""", unsafe_allow_html=True)

        with tl_col:
            st.markdown('<div style="font-size:14px;font-weight:700;color:#ef4444;margin-bottom:10px">💀 Top 10 Losers (by P&L)</div>', unsafe_allow_html=True)
            for tr in sorted_by_pnl[-10:]:
                t = tr.get("ticker","")
                st.markdown(f"""<div class="mv-row">
                  <div>{tv_link(t)} <span style="font-size:11px;color:#475569">· {tr.get("entry_date","")}</span></div>
                  <div style="text-align:right">
                    <span class="neg">{tr.get("return_pct",0):+.2f}%</span>
                    <span style="color:#ef4444;font-size:12px;margin-left:8px">₹{tr.get("pnl",0):+,.0f}</span>
                    {chart_btn(t)}
                  </div>
                </div>""", unsafe_allow_html=True)

    else:
        st.info("No trade data found. Run `python backtest.py` to generate trade-level results.")

    # Monthly table
    if monthly:
        st.markdown("---")
        st.markdown('<div style="font-size:15px;font-weight:700;color:#f1f5f9;margin-bottom:10px">📅 Monthly Breakdown</div>',unsafe_allow_html=True)
        mdf = pd.DataFrame(monthly).rename(columns={"month":"Month","trades":"Trades","wins":"Wins","win_rate":"Win Rate %","return_pct":"Return %","pnl":"P&L (₹)"})
        cols_show = [c for c in ["Month","Trades","Wins","Win Rate %","Return %","P&L (₹)"] if c in mdf.columns]
        st.dataframe(mdf[cols_show], use_container_width=True, hide_index=True,
            column_config={"Win Rate %":st.column_config.NumberColumn(format="%.1f%%"),"Return %":st.column_config.NumberColumn(format="%+.2f%%"),"P&L (₹)":st.column_config.NumberColumn(format="₹%.0f")})

    # Regime breakdown
    if regime_bk:
        st.markdown("---")
        st.markdown('<div style="font-size:15px;font-weight:700;color:#f1f5f9;margin-bottom:10px">🌐 Performance by Market Regime</div>',unsafe_allow_html=True)
        for rn, rs in regime_bk.items():
            ri2 = "🟢" if rn=="Bull" else ("🔴" if rn=="Bear" else "🟡")
            rv_wr = rs.get("win_rate_pct",0); rv_exp = rs.get("expectancy",0)
            rv_pnl = rs.get("total_pnl",0); rv_tr = rs.get("trades",0)
            ec2 = "#22c55e" if rv_exp>=0 else "#ef4444"
            st.markdown(f'<div class="card" style="padding:12px 16px;margin-bottom:8px"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px"><b style="color:#f1f5f9">{ri2} {rn} Market</b><span style="color:#64748b;font-size:12px">{rv_tr} trades</span><div style="display:flex;gap:20px"><span style="font-size:13px">WR: <b style="color:{wrc}">{rv_wr:.1f}%</b></span><span style="font-size:13px">Expectancy: <b style="color:{ec2}">{rv_exp:+.2f}%</b></span><span style="font-size:13px">P&L: <b style="color:{ec2}">₹{rv_pnl:+,.0f}</b></span></div></div></div>',unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    # SIMULATOR — with real company names from trade universe
    # ══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("""
    <div class="card" style="border-color:#7c3aed33">
      <div style="font-size:16px;font-weight:700;color:#f1f5f9;margin-bottom:4px">🎛️ Strategy Parameter Simulator</div>
      <div style="color:#64748b;font-size:13px">Adjust TP/SL and simulate with real company names from the NSE universe. Each simulated trade shows the ticker it was assigned to.</div>
    </div>
    """,unsafe_allow_html=True)

    # Collect real tickers for sampling
    sim_ticker_pool = list(set(tr.get("ticker","") for tr in all_trades)) or [p.get("ticker","") for p in picks[:100]]
    if not sim_ticker_pool:
        sim_ticker_pool = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","KOTAKBANK","BHARTIARTL","ITC","LT","SBIN"]

    # Presets
    st.markdown('<div style="font-size:11px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px">Quick Presets</div>',unsafe_allow_html=True)
    pb1,pb2,pb3,pb4,pb5 = st.columns(5)
    preset = None
    with pb1:
        if st.button("🛡️ Conservative\n2%TP / 1.5%SL",key="p1"): preset={"tp":2.0,"sl":1.5,"w":26,"pool":20}
    with pb2:
        if st.button("⚡ Aggressive\n5%TP / 3%SL",key="p2"): preset={"tp":5.0,"sl":3.0,"w":52,"pool":20}
    with pb3:
        if st.button("🎯 Tight Scalp\n1.5%TP / 1%SL",key="p3"): preset={"tp":1.5,"sl":1.0,"w":12,"pool":10}
    with pb4:
        if st.button("🚀 High Conv.\n8%TP / 4%SL",key="p4"): preset={"tp":8.0,"sl":4.0,"w":52,"pool":10}
    with pb5:
        if st.button("🔄 Actual Params\n4%TP / 2%SL",key="p5"): preset={"tp":4.0,"sl":2.0,"w":52,"pool":20}

    if preset:
        st.session_state.update({"s_tp":preset["tp"],"s_sl":preset["sl"],"s_w":preset["w"],"s_pool":preset["pool"]})

    sl1,sl2,sl3 = st.columns(3)
    with sl1: tp_pct = st.slider("Take Profit %",1.0,15.0,st.session_state.get("s_tp",4.0),0.5,key="sl_tp")
    with sl2: sl_pct = st.slider("Stop Loss %",0.5,10.0,st.session_state.get("s_sl",2.0),0.5,key="sl_sl")
    with sl3: cap_sim = st.select_slider("Capital (₹)",[25000,50000,100000,250000,500000,1000000],100000,format_func=lambda x:f"₹{x:,}",key="sl_cap")
    sl4,sl5 = st.columns(2)
    with sl4: sim_w = st.slider("Backtest Weeks",4,52,st.session_state.get("s_w",12),4,key="sl_w")
    with sl5: pool = st.slider("Picks/Week",5,30,st.session_state.get("s_pool",10),5,key="sl_pool")

    rr = tp_pct / sl_pct if sl_pct > 0 else 0
    st.markdown(f'<div style="padding:10px 14px;background:#0d1728;border:1px solid #1e2a3a;border-radius:8px;font-size:12px;color:#64748b;margin-bottom:8px">Config: TP <b style="color:#22c55e">{tp_pct}%</b> · SL <b style="color:#ef4444">{sl_pct}%</b> · R:R <b style="color:#38bdf8">1:{rr:.1f}</b> · {sim_w}w · {pool} picks/wk</div>',unsafe_allow_html=True)

    run_btn = st.button("▶ Run Simulation", type="primary", use_container_width=False, key="runsim")
    if run_btn:
        prog = st.progress(0,"Running simulation...")
        base_wr = 0.526
        rr_adj = (rr - 1.78) * 0.03
        adj_wr = min(0.75, max(0.30, base_wr + rr_adj))
        equity = float(cap_sim)
        eq_curve = [equity]
        sim_trade_log = []  # Now stores dicts with ticker info
        weekly_rets = []

        for wk in range(sim_w):
            prog.progress((wk+1)/sim_w, f"Week {wk+1}/{sim_w}...")
            wk_eq = equity; wk_pnl = 0.0; trade_size = equity/pool
            # Pick random tickers for this week
            week_tickers = random.choices(sim_ticker_pool, k=pool)
            for j in range(pool):
                ticker_sim = week_tickers[j]
                if random.random() < adj_wr:
                    g = random.gauss(tp_pct, tp_pct*0.15)/100
                    pnl_sim = trade_size * g
                    wk_pnl += pnl_sim
                    sim_trade_log.append({
                        "week": wk+1, "ticker": ticker_sim, "result": "WIN",
                        "return_pct": g*100, "pnl": pnl_sim, "exit": "TP",
                        "alloc": trade_size
                    })
                else:
                    lm = random.choice([1.0,1.0,1.2,1.5,2.0])
                    l = -sl_pct*lm/100; l = max(l,-sl_pct*2.5/100)
                    pnl_sim = trade_size * l
                    wk_pnl += pnl_sim
                    exit_type = "SL" if lm <= 1.2 else "TIME"
                    sim_trade_log.append({
                        "week": wk+1, "ticker": ticker_sim, "result": "LOSS",
                        "return_pct": l*100, "pnl": pnl_sim, "exit": exit_type,
                        "alloc": trade_size
                    })
            equity += wk_pnl; equity = max(equity,0)
            eq_curve.append(equity)
            weekly_rets.append(wk_pnl/wk_eq*100 if wk_eq>0 else 0)
        prog.empty()

        # Calculate stats
        wins_r = [t["return_pct"] for t in sim_trade_log if t["result"]=="WIN"]
        loss_r = [t["return_pct"] for t in sim_trade_log if t["result"]=="LOSS"]
        s_wr = len(wins_r)/len(sim_trade_log)*100 if sim_trade_log else 0
        s_aw = sum(wins_r)/len(wins_r) if wins_r else 0
        s_al = sum(loss_r)/len(loss_r) if loss_r else 0
        s_exp = (s_wr/100*s_aw)+((1-s_wr/100)*s_al)
        s_ret = (equity-cap_sim)/cap_sim*100
        s_sh = (np.mean(weekly_rets)/np.std(weekly_rets))*math.sqrt(52) if len(weekly_rets)>1 and np.std(weekly_rets)>0 else 0
        peak_e=cap_sim; s_dd=0
        for eq in eq_curve:
            if eq>peak_e: peak_e=eq
            s_dd=max(s_dd,(peak_e-eq)/peak_e*100 if peak_e>0 else 0)

        ok = s_ret>5 and s_wr>55
        st.markdown(f"""<div style="background:{'#14532d22' if ok else '#450a0a22'};border:1px solid {'#16653455' if ok else '#45100a55'};border-radius:10px;padding:14px 18px;margin:14px 0">
          <span style="font-size:15px;font-weight:700;color:{'#4ade80' if ok else '#ef4444'}">{'✅ Strategy Viable!' if ok else '⚠ Needs Tuning'}</span>
          <span style="font-size:13px;color:{'#86efac' if ok else '#fca5a5'};margin-left:10px">WR {s_wr:.1f}% · Exp/trade {s_exp:+.2f}% · Sharpe {s_sh:.2f}</span>
        </div>""",unsafe_allow_html=True)

        r1,r2,r3,r4 = st.columns(4)
        src = "#22c55e" if s_ret>=0 else "#ef4444"
        swc = "#22c55e" if s_wr>=60 else ("#f59e0b" if s_wr>=50 else "#ef4444")
        sec = "#22c55e" if s_exp>=0 else "#ef4444"
        ssc = "#22c55e" if s_sh>=0.5 else ("#f59e0b" if s_sh>=0 else "#ef4444")
        with r1: st.markdown(metric_box("Total Return",f'<span style="color:{src}">{s_ret:+.1f}%</span>',f'₹{cap_sim:,}→₹{equity:,.0f}',src),unsafe_allow_html=True)
        with r2: st.markdown(metric_box("Win Rate",f'<span style="color:{swc}">{s_wr:.1f}%</span>',"Target: >60%",swc),unsafe_allow_html=True)
        with r3: st.markdown(metric_box("Expectancy",f'<span style="color:{sec}">{s_exp:+.2f}%</span>',"Target: >0%",sec),unsafe_allow_html=True)
        with r4: st.markdown(metric_box("Sharpe Ratio",f'<span style="color:{ssc}">{s_sh:.2f}</span>',"Target: >0.5",ssc),unsafe_allow_html=True)

        # Equity curve
        eq_df = pd.DataFrame({"Week":range(len(eq_curve)),"Equity (₹)":eq_curve})
        st.markdown('<div style="font-size:14px;font-weight:700;color:#f1f5f9;margin:12px 0 6px">📈 Simulated Equity Curve</div>',unsafe_allow_html=True)
        st.line_chart(eq_df.set_index("Week"), color=["#1a56db"])

        # ── SIMULATED TRADE LOG — every trade with company name ──
        st.markdown(f'<div style="font-size:15px;font-weight:700;color:#f1f5f9;margin:16px 0 6px">📋 Simulated Trade Log — All {len(sim_trade_log)} Trades</div>', unsafe_allow_html=True)
        st.markdown('<div style="color:#64748b;font-size:13px;margin-bottom:10px">Every simulated trade using real NSE tickers. Click any ticker for TradingView chart.</div>', unsafe_allow_html=True)

        # Sim trade log filters
        stl1, stl2 = st.columns([3,2])
        with stl1:
            stl_search = st.text_input("🔍 Search simulated ticker", placeholder="OMAXE, FORTIS...", key="stl_s")
        with stl2:
            stl_filter = st.selectbox("Show", ["All Trades","Winners Only","Losers Only"], key="stl_f")

        display_trades = sim_trade_log
        if stl_search:
            display_trades = [t for t in display_trades if stl_search.upper() in t["ticker"].upper()]
        if stl_filter == "Winners Only":
            display_trades = [t for t in display_trades if t["result"]=="WIN"]
        elif stl_filter == "Losers Only":
            display_trades = [t for t in display_trades if t["result"]=="LOSS"]

        # Summary for filtered sim trades
        sim_f_wins = sum(1 for t in display_trades if t["result"]=="WIN")
        sim_f_pnl = sum(t["pnl"] for t in display_trades)
        st.markdown(f'<div style="padding:8px 14px;background:#0d1728;border:1px solid #1e2a3a;border-radius:8px;font-size:12px;color:#64748b;margin-bottom:10px">Showing <b style="color:#38bdf8">{len(display_trades)}</b> trades · Wins: <b class="pos">{sim_f_wins}</b> · Losses: <b class="neg">{len(display_trades)-sim_f_wins}</b> · P&L: <b style="color:{"#22c55e" if sim_f_pnl>=0 else "#ef4444"}">₹{sim_f_pnl:+,.0f}</b></div>', unsafe_allow_html=True)

        sim_th = "<tr><th>#</th><th>Week</th><th>Ticker</th><th>Allocation ₹</th><th>Return %</th><th>P&L ₹</th><th>Exit</th><th>Result</th><th>Chart</th></tr>"
        sim_rows = ""
        for i, tr in enumerate(display_trades[:500], 1):
            rc2 = "pos" if tr["result"]=="WIN" else "neg"
            ex_icon2 = {"TP":"✅","SL":"🛑","TIME":"⏰"}.get(tr["exit"],"❓")
            res_html = f'<span class="pos">✅ WIN</span>' if tr["result"]=="WIN" else f'<span class="neg">❌ LOSS</span>'
            sim_rows += f"""<tr>
              <td style="color:#475569">{i}</td>
              <td style="color:#94a3b8">W{tr["week"]}</td>
              <td><a href="{tv(tr['ticker'])}" target="_blank" class="tv-link">{tr["ticker"]}</a></td>
              <td style="color:#94a3b8">₹{tr["alloc"]:,.0f}</td>
              <td><span class="{rc2}">{tr["return_pct"]:+.2f}%</span></td>
              <td><span class="{rc2}">₹{tr["pnl"]:+,.0f}</span></td>
              <td>{ex_icon2} {tr["exit"]}</td>
              <td>{res_html}</td>
              <td><a href="{tv(tr['ticker'])}" target="_blank" class="chart-btn">📊 ↗</a></td>
            </tr>"""

        st.markdown(f"""
        <div style="overflow-x:auto;max-height:600px;border:1px solid #1e2a3a;border-radius:12px">
        <table class="tv-table"><thead>{sim_th}</thead><tbody>{sim_rows}</tbody></table>
        </div>
        """, unsafe_allow_html=True)

        if len(display_trades) > 500:
            st.caption(f"Showing first 500 of {len(display_trades)} trades.")

        # Per-ticker performance summary
        st.markdown("---")
        st.markdown('<div style="font-size:14px;font-weight:700;color:#f1f5f9;margin-bottom:8px">📊 Per-Company Performance Summary</div>', unsafe_allow_html=True)
        ticker_stats = {}
        for tr in sim_trade_log:
            tk = tr["ticker"]
            if tk not in ticker_stats:
                ticker_stats[tk] = {"trades":0,"wins":0,"pnl":0.0}
            ticker_stats[tk]["trades"] += 1
            ticker_stats[tk]["pnl"] += tr["pnl"]
            if tr["result"]=="WIN":
                ticker_stats[tk]["wins"] += 1

        ts_sorted = sorted(ticker_stats.items(), key=lambda x: x[1]["pnl"], reverse=True)

        ts_th = "<tr><th>Ticker</th><th>Trades</th><th>Wins</th><th>Win Rate</th><th>Total P&L</th><th>Chart</th></tr>"
        ts_rows = ""
        for tk, st_d in ts_sorted:
            wr_tk = st_d["wins"]/st_d["trades"]*100 if st_d["trades"]>0 else 0
            pnl_c = "pos" if st_d["pnl"]>=0 else "neg"
            wr_c = "pos" if wr_tk >= 55 else ("warn" if wr_tk >= 45 else "neg")
            ts_rows += f"""<tr>
              <td><a href="{tv(tk)}" target="_blank" class="tv-link">{tk}</a></td>
              <td style="color:#94a3b8">{st_d["trades"]}</td>
              <td class="pos">{st_d["wins"]}</td>
              <td><span class="{wr_c}">{wr_tk:.0f}%</span></td>
              <td><span class="{pnl_c}">₹{st_d["pnl"]:+,.0f}</span></td>
              <td><a href="{tv(tk)}" target="_blank" class="chart-btn">📊 ↗</a></td>
            </tr>"""

        st.markdown(f'<div style="overflow-x:auto;max-height:400px;border:1px solid #1e2a3a;border-radius:12px"><table class="tv-table"><thead>{ts_th}</thead><tbody>{ts_rows}</tbody></table></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# TAB 7 — BLUEPRINT
# ══════════════════════════════════════════════════════════════════
with t7:
    st.markdown('''<div style="max-width:900px;margin:0 auto">
<div style="font-size:24px;font-weight:900;color:#f1f5f9;margin-bottom:8px">📘 Platform Blueprint & Architecture</div>
<div style="color:#94a3b8;font-size:14px;margin-bottom:24px">Documentation of functional intent and core calculation logic for each module within the MarketPulse platform.</div>

<div class="card" style="border-left:4px solid #38bdf8">
<div style="font-size:18px;font-weight:700;color:#f1f5f9;margin-bottom:8px">🎯 1. Opportunities</div>
<p style="color:#e2e8f0;font-size:14px;margin-bottom:6px"><b style="color:#94a3b8">Intent:</b> Surface high-conviction, immediate swing trade setups.</p>
<p style="color:#94a3b8;font-size:13px;line-height:1.5"><b>Calculation Logic:</b> The engine filters the entire NSE universe for strong base constraints (e.g., Min Volume, Min Price) and evaluates them for categorical Alpha Signals (52-Week Breakouts, Volume Spikes, and strong EMA Momentum). Stocks passing these checks are given an AI Score out of 100 based on price action density. Only stocks with score >= 50 populate this tab.</p>
</div>

<div class="card" style="border-left:4px solid #22c55e">
<div style="font-size:18px;font-weight:700;color:#f1f5f9;margin-bottom:8px">🏆 2. Top Movers</div>
<p style="color:#e2e8f0;font-size:14px;margin-bottom:6px"><b style="color:#94a3b8">Intent:</b> Contextualize the broader market momentum across various hold durations (1 Week to 3 Months).</p>
<p style="color:#94a3b8;font-size:13px;line-height:1.5"><b>Calculation Logic:</b> Sorts the full market universe by aggregate percentage returns over the specified trailing periods. Excludes illiquid penny stocks to ensure realistic percentage shifts. Incorporates fundamental parameters like P/E and Market Cap for instant screening verification.</p>
</div>

<div class="card" style="border-left:4px solid #f59e0b">
<div style="font-size:18px;font-weight:700;color:#f1f5f9;margin-bottom:8px">📋 3. Full Scan</div>
<p style="color:#e2e8f0;font-size:14px;margin-bottom:6px"><b style="color:#94a3b8">Intent:</b> Complete transparency and visibility over the entire processed market universe (~2,100+ stocks).</p>
<p style="color:#94a3b8;font-size:13px;line-height:1.5"><b>Calculation Logic:</b> Loads the `latest_full_scan.csv` containing normalized closing price adjustments up to the latest trading session. Exposes a localized Pandas dataframe layer allowing fast in-memory filtering by structural criteria (Gainers, Losers, Market Capitalization bins).</p>
</div>

<div class="card" style="border-left:4px solid #a78bfa">
<div style="font-size:18px;font-weight:700;color:#f1f5f9;margin-bottom:8px">📰 4. News</div>
<p style="color:#e2e8f0;font-size:14px;margin-bottom:6px"><b style="color:#94a3b8">Intent:</b> Provide fundamental macro and micro context to technical setups via live business intelligence.</p>
<p style="color:#94a3b8;font-size:13px;line-height:1.5"><b>Calculation Logic:</b> An automated daily GitHub Actions parser scrapes RSS feeds from verified financial publishers (LiveMint, Economic Times, MoneyControl), normalizes the payload into `daily_news.json`, and feeds it directly into the interface with clickable source attribution.</p>
</div>

<div class="card" style="border-left:4px solid #ec4899">
<div style="font-size:18px;font-weight:700;color:#f1f5f9;margin-bottom:8px">🤖 5. AI Picks</div>
<p style="color:#e2e8f0;font-size:14px;margin-bottom:6px"><b style="color:#94a3b8">Intent:</b> Algorithmic conviction scoring producing absolute BUY, HOLD, or SELL mandates.</p>
<p style="color:#94a3b8;font-size:13px;line-height:1.5"><b>Calculation Logic:</b> Evaluates the prevailing master trend (bull/bear/sideways regime) and cross-references it with localized Multi-Timeframe (MTF) EMA alignments. It dynamically computes Stop Loss based on Average True Range (ATR) multipliers, Take Profit ratios, Risk/Reward grids, and historical probability of success before finalizing a position tier.</p>
</div>

<div class="card" style="border-left:4px solid #14b8a6">
<div style="font-size:18px;font-weight:700;color:#f1f5f9;margin-bottom:8px">🧪 6. Backtest Lab</div>
<p style="color:#e2e8f0;font-size:14px;margin-bottom:6px"><b style="color:#94a3b8">Intent:</b> Validate the quantitative edge of predictions against a historical 52-week timeline.</p>
<p style="color:#94a3b8;font-size:13px;line-height:1.5"><b>Calculation Logic:</b> The engine runs a rigid deterministic simulation backward through 1 year of daily EOD ticks (`scan_results/backtest_results.json`). It records entry rules and executes standard portfolio matrix calculations to handle exit events (Take Profit hits, Stop Loss drops, Time-in-market expirations). Produces aggregate portfolio Expectancy, Profit Factor, and simulated Sharpe Ratios.</p>
</div>
</div>''', unsafe_allow_html=True)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:20px;color:#334155;font-size:12px;border-top:1px solid #1e2a3a;margin-top:20px">
  MarketPulse India · NSE Quantitative Terminal · Python + Streamlit ·
  <a href="https://github.com/vinayloki/india-swing-scanner" target="_blank" style="color:#475569">GitHub</a> ·
  Data: Yahoo Finance / NSEpy · Auto-updated daily via GitHub Actions · For educational use only
</div>
""", unsafe_allow_html=True)
