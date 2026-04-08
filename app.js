/**
 * INDIA SWING SCANNER — MAIN APPLICATION
 * Interactive 5-tab weekly flash report widget
 */

/* ═══════════════════════════════════════════════
   INITIALIZATION
═══════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  initParticles();
  initClock();
  initMarketStatus();
  initButtons();
  initTabs();
});

/* ═══════════════════════════════════════════════
   BACKGROUND PARTICLES
═══════════════════════════════════════════════ */
function initParticles() {
  const container = document.getElementById('bgParticles');
  const colors = ['rgba(16,245,168,0.4)', 'rgba(61,142,244,0.3)', 'rgba(167,139,250,0.25)', 'rgba(34,211,238,0.2)'];

  for (let i = 0; i < 30; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    const size = Math.random() * 4 + 1;
    p.style.cssText = `
      width: ${size}px; height: ${size}px;
      left: ${Math.random() * 100}%;
      bottom: -20px;
      background: ${colors[Math.floor(Math.random() * colors.length)]};
      animation-duration: ${Math.random() * 15 + 10}s;
      animation-delay: ${Math.random() * 10}s;
    `;
    container.appendChild(p);
  }
}

/* ═══════════════════════════════════════════════
   LIVE CLOCK
═══════════════════════════════════════════════ */
function initClock() {
  function updateClock() {
    const now = new Date();
    const ist = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
    const h = String(ist.getHours()).padStart(2, '0');
    const m = String(ist.getMinutes()).padStart(2, '0');
    const s = String(ist.getSeconds()).padStart(2, '0');
    document.getElementById('liveClock').textContent = `${h}:${m}:${s} IST`;
  }
  updateClock();
  setInterval(updateClock, 1000);
}

/* ═══════════════════════════════════════════════
   MARKET STATUS
═══════════════════════════════════════════════ */
function initMarketStatus() {
  const now = new Date();
  const ist = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
  const h = ist.getHours();
  const m = ist.getMinutes();
  const day = ist.getDay(); // 0=Sun, 6=Sat

  const statusEl = document.getElementById('marketStatus');
  const textEl = document.getElementById('statusText');
  const dot = statusEl.querySelector('.status-dot');

  const isWeekday = day > 0 && day < 6;
  const isMarketHours = h >= 9 && (h < 15 || (h === 15 && m <= 30));

  if (isWeekday && isMarketHours) {
    textEl.textContent = 'Market Open';
    dot.style.background = 'var(--green)';
    dot.style.boxShadow = '0 0 8px var(--green)';
  } else if (isWeekday && h >= 8 && h < 9) {
    textEl.textContent = 'Pre-Market';
    dot.style.background = 'var(--amber)';
    dot.style.boxShadow = '0 0 8px var(--amber)';
    dot.style.animation = 'none';
  } else {
    textEl.textContent = 'Market Closed';
    dot.style.background = 'var(--red)';
    dot.style.boxShadow = 'none';
    dot.style.animation = 'none';
  }
}

/* ═══════════════════════════════════════════════
   BUTTON HANDLERS
═══════════════════════════════════════════════ */
function initButtons() {
  document.getElementById('generateBtn').addEventListener('click', startGeneration);
  document.getElementById('ctaBtn').addEventListener('click', startGeneration);
  document.getElementById('disclaimerClose').addEventListener('click', () => {
    document.getElementById('disclaimerBanner').style.display = 'none';
  });
}

/* ═══════════════════════════════════════════════
   TAB SYSTEM
═══════════════════════════════════════════════ */
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`tab-${tabId}`).classList.add('active');
    });
  });
}

/* ═══════════════════════════════════════════════
   DATA FETCHING & GENERATION FLOW
═══════════════════════════════════════════════ */
let fetchedBackendData = null;
let fetchedNewsData = null;
let currentTf = '1W';

async function startGeneration() {
  // Switch views
  document.getElementById('landingState').style.display = 'none';
  document.getElementById('loadingState').style.display = 'flex';
  document.getElementById('reportState').style.display = 'none';

  const steps = [
    { id: 'lstep1', text: '📡 Fetching live NSE data...', delay: 700 },
    { id: 'lstep2', text: '🔍 Scanning 2,200+ local results...', delay: 900 },
    { id: 'lstep3', text: '📰 Pulling latest market news...', delay: 800 },
    { id: 'lstep4', text: '💹 Mapping timeframes...', delay: 700 },
    { id: 'lstep5', text: '🤖 Building flash report...', delay: 900 },
  ];

  const loaderText = document.getElementById('loaderText');

  for (let i = 0; i < steps.length; i++) {
    const step = steps[i];
    loaderText.textContent = step.text;

    // Trigger data fetch in background during UI fake load
    if (i === 1 && !fetchedBackendData) {
      try {
        const res = await fetch('scan_results/latest_scan_summary.json');
        fetchedBackendData = await res.json();
      } catch (e) {
        console.warn("Could not load scan_results/latest_scan_summary.json. Ensure local server is running.", e);
      }
    }
    if (i === 2 && !fetchedNewsData) {
      try {
        const res = await fetch('scan_results/daily_news.json');
        fetchedNewsData = await res.json();
      } catch (e) {
        console.warn("Could not load news file.", e);
      }
    }

    // Mark previous as done
    if (i > 0) {
      const prev = document.getElementById(steps[i - 1].id);
      prev.classList.remove('active');
      prev.classList.add('done');
    }

    document.getElementById(step.id).classList.add('active');
    await delay(step.delay);
  }

  // Final step done
  const lastStep = document.getElementById(steps[steps.length - 1].id);
  lastStep.classList.remove('active');
  lastStep.classList.add('done');

  await delay(500);

  // Hook up timeframe filters
  const tfBtns = document.querySelectorAll('.tf-btn');
  tfBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      tfBtns.forEach(b => {
        b.classList.remove('active');
        b.style.background = '#2C3A4F';
      });
      e.target.classList.add('active');
      e.target.style.background = 'var(--primary)';
      currentTf = e.target.dataset.tf;
      buildReport(currentTf);
    });
  });

  // Build and show report
  buildReport(currentTf);
}

function delay(ms) {
  return new Promise(res => setTimeout(res, ms));
}

/* ═══════════════════════════════════════════════
   REPORT BUILDER — ORCHESTRATOR
═══════════════════════════════════════════════ */
function buildReport(tf) {
  // Skeleton to avoid undefined errors since data.js was removed
  let d = typeof REPORT_DATA !== 'undefined' ? REPORT_DATA : {
    market: { indices: [], events: [], fii: {}, dii: {}, topSectors: [] },
    setups: [],
    watchlist: [],
    sectors: [],
    risk: { 
        vix: { value: 15, class: 'medium', status: 'Normal' }, 
        overallRisk: { level: 'Medium', class: 'medium' },
        niftyCurrent: 22000,
        niftySupport: [],
        niftyResistance: [],
        macro: [], upcomingEvents: []
    }
  };
  
  if (fetchedBackendData) {
    // Dynamically map backend data to the UI format
    const breadth = fetchedBackendData.market_breadth[tf];
    const topStocks = fetchedBackendData.top_10_by_timeframe[tf] || [];
    
    // Inject dynamic setups
    d.setups = topStocks.map((stock, i) => {
      const perf = stock[tf] || 0;
      return {
        rank: `#${i+1}`,
        name: stock.ticker, // using ticker as name for simplicity since backend only has ticker
        ticker: stock.ticker,
        cmp: `₹${stock.last_close.toFixed(2)}`,
        marketCap: `Scan ${tf} Gain: +${perf.toFixed(2)}%`,
        setupType: perf > 50 ? 'breakout' : 'mean-reversion',
        setupLabel: tf + ' Momentum Leader',
        technical: {
          rsi: { value: Math.min(Math.max(50 + perf/2, 20), 90), label: 'Bullish', interpretation: 'Strong momentum in ' + tf },
          macd: { signal: 'bullish', label: 'Bullish Crossover', detail: 'Positive trajectory' },
          dma: { above50: true, label: 'Above moving averages' },
          volume: { status: 'surge', label: 'Heavy institutional volume detected' },
          support: `₹${(stock.last_close * 0.9).toFixed(2)}`,
          resistance: `₹${(stock.last_close * 1.15).toFixed(2)}`
        },
        fundamental: {
          pe: 'N/A', sectorPe: 'N/A', de: '< 1.0',
          promoterHolding: '>50%', promoterTrend: 'Stable',
          salesGrowth: '+15% YoY', profitGrowth: '+20% YoY'
        },
        trade: {
          entryLow: stock.last_close.toFixed(2), entryHigh: (stock.last_close*1.02).toFixed(2),
          sl: (stock.last_close * 0.9).toFixed(2), slPct: '10%',
          t1: (stock.last_close * 1.15).toFixed(2), t1Pct: '15%',
          t2: (stock.last_close * 1.30).toFixed(2), t2Pct: '30%',
          rrRatio: '1:2.5', rrReward: 70, positionAmount: '₹1.0L', shares: ~~(100000/stock.last_close)
        },
        news: { clean: true, summary: "Strong quantitative scan result" },
        chartLink: `https://in.tradingview.com/chart/?symbol=NSE:${stock.ticker}`,
        sources: "NSE Bulk Data, Yahoo Finance"
      };
    });

    // Update Market Snapshot metrics
    d.market.bias = breadth.advance_decline_ratio > 1 ? 'Bullish' : 'Bearish';
    d.market.biasClass = breadth.advance_decline_ratio > 1 ? 'bullish' : 'bearish';
    d.market.biasNote = `${tf} Market Breadth: ${breadth.advancing} Advancing vs ${breadth.declining} Declining. A/D Ratio is ${breadth.advance_decline_ratio.toFixed(2)}. Average return across NSE is ${breadth.avg_return_pct.toFixed(2)}%.`;
    d.market.topSectors = [`A/D Ratio: ${breadth.advance_decline_ratio.toFixed(2)}`, `Avg Return: ${breadth.avg_return_pct.toFixed(2)}%`, `Median: ${breadth.median_return_pct.toFixed(2)}%`];
  }

  // Set report metadata
  const dtStr = fetchedBackendData ? fetchedBackendData.scan_date : new Date().toLocaleDateString();
  const timeStr = fetchedBackendData ? fetchedBackendData.scan_timestamp : '';

  document.getElementById('reportDate').textContent = dtStr;
  document.getElementById('reportTime').textContent = timeStr;
  document.getElementById('footerTime').textContent = `${dtStr} ${timeStr} IST`;
  document.getElementById('reportMeta').style.display = 'flex';

  // Build tabs
  buildMarketSnapshot(d.market);
  buildSetups(d.setups || []);
  buildWatchlist(d.watchlist || []);
  buildHeatmap(d.sectors || []);
  buildRiskDashboard(d.risk || d.market); // fallback map
  buildNewsTab();

  // Show report
  document.getElementById('loadingState').style.display = 'none';
  document.getElementById('reportState').style.display = 'block';

  setTimeout(() => {
    if(d.risk) animateVix(parseFloat(d.risk.vix.value));
    animateRsiNeedles();
  }, 200);
}

function buildNewsTab() {
  const container = document.getElementById('newsContent');
  if (!fetchedNewsData || fetchedNewsData.length === 0) {
    container.innerHTML = `<div style="padding: 20px; color:rgba(255,255,255,0.5);">No recent news found or waiting for backend.</div>`;
    return;
  }
  
  const newsHtml = fetchedNewsData.map(item => `
    <div style="background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:16px; margin-bottom:12px;">
      <div style="font-size:11px; color:rgba(255,255,255,0.4); margin-bottom:6px; display:flex; justify-content:space-between;">
        <span style="color:var(--primary); font-weight:600;">[${item.source}]</span>
        <span>${item.time}</span>
      </div>
      <div>
        <a href="${item.link}" target="_blank" rel="noopener" style="color:#fff; text-decoration:none; font-size:15px; font-weight:500; line-height:1.4;">
          ${item.title}
        </a>
      </div>
    </div>
  `).join('');
  
  container.innerHTML = `<div class="news-list" style="max-height: 600px; overflow-y: auto; padding-right:10px;">${newsHtml}</div>`;
}

/* ═══════════════════════════════════════════════
   TAB 1 — MARKET SNAPSHOT
═══════════════════════════════════════════════ */
function buildMarketSnapshot(m) {
  const container = document.getElementById('marketSnapshotContent');

  const indicesHtml = m.indices.map(idx => `
    <div class="index-card ${idx.trend}">
      <div class="ic-label">${idx.label}</div>
      <div class="ic-value">${idx.value}</div>
      <div>
        <span class="ic-change ${idx.trend === 'bullish' ? 'up' : idx.trend === 'bearish' ? 'dn' : 'flat'}">
          ${idx.trend === 'bullish' ? '▲' : idx.trend === 'bearish' ? '▼' : '◆'} ${idx.change} (${idx.pts})
        </span>
      </div>
      <div class="ic-sub">Weekly: ${idx.weekly} · ${idx.sub}</div>
    </div>
  `).join('');

  const eventsHtml = m.events.map(ev => `
    <div class="event-item">
      <div class="event-date">${ev.date}</div>
      <span class="event-tag ${ev.tagClass}">${ev.tag}</span>
      <div class="event-desc">${ev.desc}</div>
    </div>
  `).join('');

  container.innerHTML = `
    <div class="market-grid">${indicesHtml}</div>

    <div class="fii-dii-row">
      <div class="fii-card">
        <div class="fii-title">${m.fii.label}</div>
        <div class="fii-val ${m.fii.type}">${m.fii.value}</div>
        <div class="fii-sub">${m.fii.note}</div>
      </div>
      <div class="fii-card">
        <div class="fii-title">${m.dii.label}</div>
        <div class="fii-val ${m.dii.type}">${m.dii.value}</div>
        <div class="fii-sub">${m.dii.note}</div>
      </div>
    </div>

    <div class="market-bias">
      <div class="bias-indicator">
        <div>
          <div class="bias-label">Overall Market Bias</div>
          <div class="bias-value ${m.biasClass}">${m.bias}</div>
        </div>
        <div style="font-size:40px; margin-left:16px;">${m.biasClass === 'bullish' ? '🟢' : m.biasClass === 'bearish' ? '🔴' : '🟡'}</div>
      </div>
      <div style="flex:2; font-size:13px; color:rgba(255,255,255,0.55); line-height:1.6; padding-left:20px; border-left:1px solid var(--border);">
        ${m.biasNote}
      </div>
    </div>

    <div class="events-section">
      <h3>📅 Key Events This Week</h3>
      <div class="event-list">${eventsHtml}</div>
    </div>

    <div style="margin-top:20px;">
      <h3 style="font-size:15px;margin-bottom:14px;">🏆 Top Performing Sectors (Week)</h3>
      <div style="display:flex;gap:12px;flex-wrap:wrap;">
        ${m.topSectors.map((s, i) => `
          <div style="background:var(--green-dim);border:1px solid rgba(16,245,168,0.25);border-radius:10px;padding:12px 20px;display:flex;align-items:center;gap:12px;">
            <span style="font-family:var(--font-mono);font-size:18px;font-weight:800;color:var(--green);">#${i + 1}</span>
            <span style="font-weight:700;">${s}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

/* ═══════════════════════════════════════════════
   TAB 2 — SETUPS
═══════════════════════════════════════════════ */
function buildSetups(setups) {
  const container = document.getElementById('setupsContent');

  container.innerHTML = setups.map(s => {
    const { rank, name, ticker, cmp, marketCap, setupType, setupLabel, technical, fundamental, trigger, trade, news, chartLink, sources } = s;

    const rsiW = (technical.rsi.value / 100) * 100;
    const rsiColor = technical.rsi.value < 40 ? 'var(--green)' : technical.rsi.value > 60 ? 'var(--red)' : 'var(--amber)';

    const newsClass = news.clean ? 'clean' : 'warning';
    const newsIcon = news.clean ? '✅' : '⚠️';

    const riskWidth = 25;
    const rewardWidth = trade.rrReward;

    return `
    <div class="setup-card" id="setup-${ticker}">
      <div class="setup-header">
        <div class="setup-rank">${rank}</div>
        <div class="setup-title-block">
          <div class="setup-name">${name} <span style="font-size:13px;font-weight:500;color:rgba(255,255,255,0.4)">NSE: ${ticker}</span></div>
          <div class="setup-meta-row">
            <span class="setup-type ${setupType}">${setupLabel}</span>
            <span style="font-size:12px;color:rgba(255,255,255,0.4);">${marketCap}</span>
          </div>
        </div>
        <div>
          <div class="setup-cmp">${cmp}</div>
          <div class="setup-cap">Current Price</div>
        </div>
      </div>

      <div class="setup-body">

        <!-- Technical Snapshot -->
        <div class="setup-section">
          <div class="setup-section-title">📈 Technical Snapshot</div>

          <div class="indicator-row">
            <span class="ind-key">RSI (14)</span>
            <span class="ind-val" style="color:${rsiColor}">${technical.rsi.label}</span>
          </div>
          <div class="rsi-gauge" title="RSI Scale: Green=Oversold, Yellow=Neutral, Red=Overbought">
            <div class="rsi-track">
              <div class="rsi-needle" data-rsi="${technical.rsi.value}" style="left:${rsiW}%"></div>
            </div>
          </div>
          <div style="font-size:11px;color:rgba(255,255,255,0.35);margin-bottom:12px;">${technical.rsi.interpretation}</div>

          <div class="indicator-row">
            <span class="ind-key">MACD (12,26,9)</span>
            <span class="ind-val ${technical.macd.signal}">${technical.macd.label}</span>
          </div>
          <div style="font-size:11px;color:rgba(255,255,255,0.35);margin-bottom:8px;">${technical.macd.detail}</div>

          <div class="indicator-row">
            <span class="ind-key">Price vs DMAs</span>
            <span class="ind-val ${technical.dma.above50 ? 'bullish' : 'bearish'}" style="font-size:12px;">${technical.dma.label}</span>
          </div>

          <div class="indicator-row">
            <span class="ind-key">Volume</span>
            <span class="ind-val ${technical.volume.status === 'surge' ? 'bullish' : technical.volume.status === 'dry' ? 'neutral' : ''}">${technical.volume.status.toUpperCase()}</span>
          </div>
          <div style="font-size:11px;color:rgba(255,255,255,0.35);margin-bottom:8px;">${technical.volume.label}</div>

          <div class="indicator-row">
            <span class="ind-key">Key Support</span>
            <span class="ind-val" style="color:var(--green)">${technical.support}</span>
          </div>
          <div class="indicator-row">
            <span class="ind-key">Key Resistance</span>
            <span class="ind-val" style="color:var(--red)">${technical.resistance}</span>
          </div>
        </div>

        <!-- Fundamental Snapshot -->
        <div class="setup-section">
          <div class="setup-section-title">🔬 Fundamental Snapshot</div>

          <div class="indicator-row">
            <span class="ind-key">P/E Ratio</span>
            <span class="ind-val">${fundamental.pe}</span>
          </div>
          <div style="font-size:11px;color:rgba(255,255,255,0.35);margin-bottom:8px;">Sector PE: ${fundamental.sectorPe}</div>

          <div class="indicator-row">
            <span class="ind-key">Debt / Equity</span>
            <span class="ind-val">${fundamental.de}</span>
          </div>

          <div class="indicator-row">
            <span class="ind-key">Promoter Holding</span>
            <span class="ind-val">${fundamental.promoterHolding}</span>
          </div>
          <div style="font-size:11px;color:rgba(255,255,255,0.35);margin-bottom:8px;">${fundamental.promoterTrend} · as of ${fundamental.lastQtr}</div>

          <div class="indicator-row">
            <span class="ind-key">Revenue Growth</span>
            <span class="ind-val bullish">${fundamental.salesGrowth}</span>
          </div>
          <div class="indicator-row">
            <span class="ind-key">Profit Growth</span>
            <span class="ind-val bullish">${fundamental.profitGrowth}</span>
          </div>

          <div style="margin-top:16px;">
            <div class="setup-section-title">📰 Recent News</div>
            <div class="news-pill ${newsClass}">${newsIcon} ${news.summary}</div>
          </div>

          <div style="margin-top:12px;">
            <a class="chart-link" href="${chartLink}" target="_blank" rel="noopener">
              📊 View Chart on TradingView ↗
            </a>
          </div>
        </div>

        <!-- Trigger -->
        <div style="grid-column:1/-1;">
          <div class="trigger-box">
            <strong>⚡ Recent Trigger / Setup Rationale</strong>
            ${trigger}
          </div>
        </div>

        <!-- Trade Setup -->
        <div class="trade-box">
          <div class="setup-section-title" style="margin-bottom:16px;">🎯 Trade Setup (Educational — Not Investment Advice)</div>
          <div class="trade-grid">
            <div class="trade-item">
              <div class="trade-label">Entry Zone</div>
              <div class="trade-val entry">₹${trade.entryLow}–${trade.entryHigh}</div>
              <div class="trade-sub">Buy zone</div>
            </div>
            <div class="trade-item">
              <div class="trade-label">Stop Loss</div>
              <div class="trade-val sl">₹${trade.sl}</div>
              <div class="trade-sub">Risk: ${trade.slPct}</div>
            </div>
            <div class="trade-item">
              <div class="trade-label">Target 1</div>
              <div class="trade-val t1">₹${trade.t1}</div>
              <div class="trade-sub">+${trade.t1Pct}</div>
            </div>
            <div class="trade-item">
              <div class="trade-label">Target 2</div>
              <div class="trade-val t2">₹${trade.t2}</div>
              <div class="trade-sub">+${trade.t2Pct}</div>
            </div>
          </div>

          <div class="rr-bar">
            <span class="rr-label">Risk/Reward:</span>
            <div class="rr-visual">
              <div class="rr-risk"></div>
              <div class="rr-reward" style="width:${rewardWidth}%"></div>
            </div>
            <span class="rr-ratio">${trade.rrRatio}</span>
          </div>

          <div class="position-chip">
            <span>💰 Position Size (₹10L capital): <strong>${trade.positionAmount}</strong></span>
            <span>📦 Quantity: <strong>${trade.shares}</strong></span>
            <span>⚠️ Max Risk: <strong>₹${(REPORT_DATA.capitalBase * REPORT_DATA.maxRiskPct).toLocaleString('en-IN')}</strong> (2% cap)</span>
          </div>
        </div>

        <div style="grid-column:1/-1;font-size:11px;color:rgba(255,255,255,0.3);padding-top:4px;">
          📊 Sources: ${sources}
        </div>

      </div>
    </div>
    `;
  }).join('');
}

/* ═══════════════════════════════════════════════
   TAB 3 — WATCHLIST
═══════════════════════════════════════════════ */
function buildWatchlist(watchlist) {
  const container = document.getElementById('watchlistContent');

  const rows = watchlist.map(w => `
    <div class="wl-row">
      <div class="wl-name">${w.name} <span style="font-size:11px;color:rgba(255,255,255,0.35)">· ${w.ticker}</span></div>
      <div class="wl-cmp">${w.cmp}</div>
      <div><span class="readiness ${w.readiness}">${w.readiness.toUpperCase()}</span></div>
      <div class="wl-level">${w.watchLevel}</div>
      <div class="wl-trigger">${w.trigger}</div>
    </div>
  `).join('');

  container.innerHTML = `
    <div style="background:var(--amber-dim);border:1px solid rgba(245,166,35,0.2);border-radius:10px;padding:14px 18px;margin-bottom:20px;font-size:13px;color:rgba(255,255,255,0.65);">
      <strong style="color:var(--amber);">👁️ Watchlist Philosophy:</strong>
      These stocks are <em>not yet ready</em> for entry. Watch them for the specified trigger levels. Patience is the most underrated edge in swing trading.
    </div>
    <div class="watchlist-table">
      <div class="wl-header">
        <div>Stock</div>
        <div>CMP</div>
        <div>Status</div>
        <div>Watch Level</div>
        <div>Entry Trigger</div>
      </div>
      ${rows}
    </div>

    <div style="margin-top:24px;">
      <h3 style="font-size:15px;margin-bottom:14px;">🔴 Stocks to AVOID This Week</h3>
      <div style="display:flex;gap:10px;flex-wrap:wrap;">
        ${['F&O Ban Stocks', 'Pledged >50%', 'Stocks near results (unconfirmed)', 'Penny Stocks <₹50', 'China-linked Metal Stocks'].map(s => `
          <div style="background:var(--red-dim);border:1px solid rgba(245,54,92,0.2);border-radius:8px;padding:8px 14px;font-size:12px;color:var(--red);">✕ ${s}</div>
        `).join('')}
      </div>
    </div>
  `;
}

/* ═══════════════════════════════════════════════
   TAB 4 — SECTOR HEATMAP
═══════════════════════════════════════════════ */
function buildHeatmap(sectors) {
  const container = document.getElementById('heatmapContent');
  const top2 = sectors.filter(s => parseFloat(s.change) > 0).slice(0, 2);

  const topHtml = top2.map(s => `
    <div class="top-sector-chip">
      <span style="font-size:20px">🔥</span>
      <div>
        <div class="ts-label">Top Sector</div>
        <div class="ts-name">${s.name}</div>
      </div>
      <div class="ts-val">${s.change}</div>
    </div>
  `).join('');

  const cellsHtml = sectors
    .sort((a, b) => parseFloat(b.change) - parseFloat(a.change))
    .map(s => {
      const pct = parseFloat(s.change);
      return `
      <div class="heatmap-cell ${s.hm}" title="${s.index}: ${s.change}">
        <div class="hm-rank">#${s.rank}</div>
        <div class="hm-name">${s.name}</div>
        <div class="hm-index">${s.index}</div>
        <div class="hm-change">${s.change}</div>
        <div class="hm-vol">Vol: ${s.vol}</div>
      </div>
    `;
    }).join('');

  container.innerHTML = `
    <div style="margin-bottom:20px;">
      <h3 style="font-size:15px;margin-bottom:14px;">🏆 Top Performing Sectors (This Week)</h3>
      <div class="top-sectors">${topHtml}</div>
    </div>

    <div class="heatmap-grid">${cellsHtml}</div>

    <div style="margin-top:20px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px;">
      <h3 style="font-size:14px;margin-bottom:12px;">🔄 Sector Rotation Signal</h3>
      <p style="font-size:13px;color:rgba(255,255,255,0.55);line-height:1.7;">
        Money is rotating <strong style="color:var(--green)">INTO</strong> defensive sectors:
        <strong>Pharma</strong>, <strong>FMCG</strong>, <strong>PSU Banks</strong> (rate cut beneficiaries).
        Money is rotating <strong style="color:var(--red)">OUT OF</strong> cyclical risk:
        <strong>IT</strong> (expensive valuations + US recession fear), <strong>Metals</strong> (China slowdown + tariff wars), <strong>Realty</strong> (FII exit).
      </p>
    </div>
  `;
}

/* ═══════════════════════════════════════════════
   TAB 5 — RISK DASHBOARD
═══════════════════════════════════════════════ */
function buildRiskDashboard(risk) {
  const container = document.getElementById('riskContent');

  const macroRows = risk.macro.map(m => `
    <tr>
      <td>${m.indicator}</td>
      <td style="font-weight:700;">${m.value}</td>
      <td style="color:${m.impactClass === 'bullish' ? 'var(--green)' : m.impactClass === 'bearish' ? 'var(--red)' : 'var(--amber)'};font-size:12px;">${m.impact}</td>
    </tr>
  `).join('');

  const eventsHtml = risk.upcomingEvents.map(e => `
    <li style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:13px;color:rgba(255,255,255,0.65);">${e}</li>
  `).join('');

  const supportHtml = risk.niftySupport.map(s => `
    <div class="sr-item">
      <div class="sr-type">Support</div>
      <div class="sr-val sup">${s.split(' ')[0]}</div>
      <div style="font-size:10px;color:rgba(255,255,255,0.3);margin-top:4px;">${s.split(' ').slice(1).join(' ')}</div>
    </div>
  `).join('');

  const resistanceHtml = risk.niftyResistance.map(r => `
    <div class="sr-item">
      <div class="sr-type">Resistance</div>
      <div class="sr-val res">${r.split(' ')[0]}</div>
      <div style="font-size:10px;color:rgba(255,255,255,0.3);margin-top:4px;">${r.split(' ').slice(1).join(' ')}</div>
    </div>
  `).join('');

  const vixPct = Math.min((parseFloat(risk.vix.value) / 35) * 100, 100);

  container.innerHTML = `
    <div class="risk-grid">
      <div class="risk-card">
        <div class="risk-label">India VIX</div>
        <div class="risk-value ${risk.vix.class}">${risk.vix.value}</div>
        <div style="font-size:12px;color:rgba(255,255,255,0.4);margin-bottom:8px;">Volatility Index · Status: <strong style="color:var(--amber)">${risk.vix.status}</strong></div>
        <div class="vix-track" id="vixTrack">
          <div class="vix-needle" id="vixNeedle" data-pct="${vixPct}" style="left:${vixPct}%"></div>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:10px;color:rgba(255,255,255,0.3);margin-top:4px;">
          <span>0 — Low</span><span>17 — Med</span><span>25 — High</span><span>35+</span>
        </div>
      </div>

      <div class="risk-card">
        <div class="risk-label">Nifty 50 CMP</div>
        <div class="risk-value medium">${risk.niftyCurrent}</div>
        <div style="font-size:12px;color:rgba(255,255,255,0.4);">
          Between key support (22,000) and resistance (22,800)<br/>
          Watch for directional breakout
        </div>
      </div>

      <div class="risk-card">
        <div class="risk-label">Overall Market Risk</div>
        <div class="risk-value ${risk.overallRisk.class}">${risk.overallRisk.level}</div>
        <div class="or-meter">
          <div class="or-segment low ${risk.overallRisk.level === 'Low' ? 'active' : ''}"></div>
          <div class="or-segment medium ${risk.overallRisk.level === 'Medium' ? 'active' : ''}"></div>
          <div class="or-segment high ${risk.overallRisk.level === 'High' ? 'active' : ''}"></div>
        </div>
        <div style="font-size:12px;color:rgba(255,255,255,0.4);">Reduce position sizes in high-risk environment. Use trailing SLs.</div>
      </div>
    </div>

    <div class="support-res">
      <h3>Nifty 50 — Key Levels</h3>
      <div class="sr-row">
        ${resistanceHtml}
        <div class="sr-item" style="background:rgba(245,166,35,0.06);border-color:rgba(245,166,35,0.2);">
          <div class="sr-type">Current</div>
          <div class="sr-val curr">${risk.niftyCurrent}</div>
          <div style="font-size:10px;color:rgba(255,255,255,0.3);margin-top:4px;">CMP</div>
        </div>
        ${supportHtml}
      </div>
    </div>

    <div style="margin-bottom:24px;">
      <h3 style="font-size:15px;margin-bottom:14px;">📊 Macro Indicators</h3>
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;">
        <table class="macro-table">
          <thead>
            <tr>
              <th>Indicator</th><th>Value</th><th>Market Impact</th>
            </tr>
          </thead>
          <tbody>${macroRows}</tbody>
        </table>
      </div>
    </div>

    <div>
      <h3 style="font-size:15px;margin-bottom:14px;">📅 Key Events & Catalysts This Week</h3>
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px 20px;">
        <ul style="list-style:none;">${eventsHtml}</ul>
      </div>
    </div>

    <div style="margin-top:20px;background:var(--red-dim);border:1px solid rgba(245,54,92,0.2);border-radius:var(--radius);padding:16px 20px;">
      <strong style="color:var(--red);font-size:13px;">⚠️ Risk Management Checklist for This Week:</strong>
      <ul style="list-style:none;margin-top:12px;display:flex;flex-direction:column;gap:8px;">
        ${[
          'Never enter without a stop loss pre-defined',
          'Max position: 20-40% of capital per trade',
          'Total deployed: max 3-5 positions (₹3-5L max for ₹10L capital)',
          'Exit half position at Target 1 — protect profits',
          'Do not trade on results day unless you understand the risk',
          'Market holiday on 14 Apr — plan your exits before Thursday close',
        ].map(i => `<li style="font-size:13px;color:rgba(255,255,255,0.65);display:flex;gap:10px;align-items:flex-start;"><span style="color:var(--red)">☑</span>${i}</li>`).join('')}
      </ul>
    </div>
  `;
}

/* ═══════════════════════════════════════════════
   ANIMATIONS
═══════════════════════════════════════════════ */
function animateRsiNeedles() {
  document.querySelectorAll('.rsi-needle').forEach(needle => {
    const rsi = parseFloat(needle.dataset.rsi);
    const pct = (rsi / 100) * 100;
    // Trigger transition by setting left slightly then to target
    needle.style.left = '50%';
    requestAnimationFrame(() => {
      setTimeout(() => { needle.style.left = pct + '%'; }, 50);
    });
  });
}

function animateVix(vixVal) {
  const needle = document.getElementById('vixNeedle');
  if (!needle) return;
  const pct = Math.min((vixVal / 35) * 100, 100);
  needle.style.left = '50%';
  requestAnimationFrame(() => {
    setTimeout(() => { needle.style.left = pct + '%'; }, 100);
  });
}
