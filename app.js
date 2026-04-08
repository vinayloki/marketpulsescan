/**
 * INDIA SWING SCANNER — MAIN APP
 * Auto-loads all data on page open. No button click needed.
 */

/* ═══════════════════════════════════════════════════════════════
   GLOBALS
═══════════════════════════════════════════════════════════════ */
let summaryData   = null;   // latest_scan_summary.json
let fullScanData  = [];     // full_summary.json stocks array
let newsData      = [];     // daily_news.json
let staticData    = null;   // data from data.js (fallback)
let currentTf     = '1W';

// Full Scan table state
let _fsSortCol  = '1M';
let _fsSortAsc  = false;
let _fsFilter   = '';
let _fsTfFilter = '';
let _fsPage     = 0;
const FS_PAGE   = 100;

/* ═══════════════════════════════════════════════════════════════
   BOOT
═══════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initMarketStatus();
  initTabs();
  loadEverything();
});

/* ═══════════════════════════════════════════════════════════════
   CLOCK + MARKET STATUS
═══════════════════════════════════════════════════════════════ */
function initClock() {
  function tick() {
    const ist = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
    const pad = n => String(n).padStart(2,'0');
    document.getElementById('clock').textContent =
      `${pad(ist.getHours())}:${pad(ist.getMinutes())}:${pad(ist.getSeconds())} IST`;
  }
  tick();
  setInterval(tick, 1000);
}

function initMarketStatus() {
  const ist  = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const h = ist.getHours(), m = ist.getMinutes(), day = ist.getDay();
  const dot   = document.getElementById('mpdot');
  const label = document.getElementById('mpText');
  const isWeekday = day > 0 && day < 6;
  const inHours   = h > 9 || (h === 9 && m >= 15);
  const inClose   = h < 15 || (h === 15 && m <= 30);

  if (isWeekday && inHours && inClose) {
    dot.className = 'mpdot open'; label.textContent = 'Market Open';
  } else if (isWeekday && h >= 8 && h < 9) {
    dot.className = 'mpdot pre'; label.textContent = 'Pre-Market';
  } else {
    dot.className = 'mpdot closed'; label.textContent = 'Market Closed';
  }
}

/* ═══════════════════════════════════════════════════════════════
   TABS
═══════════════════════════════════════════════════════════════ */
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
    });
  });
}

/* ═══════════════════════════════════════════════════════════════
   LOAD EVERYTHING — parallel fetches, show dashboard instantly
═══════════════════════════════════════════════════════════════ */
function setStep(id, state) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `load-step ${state}`;
}

async function loadEverything() {
  try {
    setStep('ls1', 'active');

    // Fetch all 3 files in parallel — don't block on any single one
    const [summRes, fullRes, newsRes] = await Promise.allSettled([
      fetch('scan_results/latest_scan_summary.json'),
      fetch('scan_results/full_summary.json'),
      fetch('scan_results/daily_news.json'),
    ]);

    setStep('ls1', 'done'); setStep('ls2', 'active');

    // Parse summary
    if (summRes.status === 'fulfilled' && summRes.value.ok) {
      summaryData = await summRes.value.json();
    } else {
      console.warn('No summary JSON — using static fallback');
    }

    setStep('ls2', 'done'); setStep('ls3', 'active');

    // Parse full scan
    if (fullRes.status === 'fulfilled' && fullRes.value.ok) {
      const fj = await fullRes.value.json();
      fullScanData = fj.stocks || [];
      if (summaryData && fj.generated) summaryData.scan_date = fj.generated;
    }

    // Parse news
    if (newsRes.status === 'fulfilled' && newsRes.value.ok) {
      newsData = await newsRes.value.json();
    }

    setStep('ls3', 'done'); setStep('ls4', 'active');

    // Build the dashboard
    buildDashboard();
    setStep('ls4', 'done');

    // Show
    document.getElementById('loadScreen').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';

    // Animate needles after paint
    setTimeout(animateNeedles, 300);

  } catch (err) {
    console.error(err);
    document.getElementById('loadScreen').style.display = 'none';
    document.getElementById('errorScreen').style.display = 'flex';
    document.getElementById('errorBody').textContent = `Error: ${err.message}`;
  }
}

/* ═══════════════════════════════════════════════════════════════
   DASHBOARD ORCHESTRATOR
═══════════════════════════════════════════════════════════════ */
function buildDashboard() {
  // Use static data.js as fallback for setups/market/watchlist/heatmap/risk
  const S = typeof REPORT_DATA !== 'undefined' ? REPORT_DATA : null;

  // Header meta
  const scanDate = summaryData?.scan_date || (S ? S.generatedAt : '—');
  const stockCount = fullScanData.length || summaryData?.total_stocks_scanned || '—';
  document.getElementById('hScanDate').textContent = scanDate;
  document.getElementById('hStockCount').textContent = stockCount;
  document.getElementById('footerDate').textContent = scanDate;

  buildStatsRow();
  buildFullScan();
  buildSetups(currentTf);
  buildMarket(S);
  buildWatchlist(S);
  buildHeatmap(S);
  buildRisk(S);
  buildNews();
}

/* ═══════════════════════════════════════════════════════════════
   STATS ROW
═══════════════════════════════════════════════════════════════ */
function buildStatsRow() {
  const el = document.getElementById('statsRow');
  const total   = fullScanData.length;
  const g1W     = fullScanData.filter(s => s['1W'] > 0).length;
  const g1M     = fullScanData.filter(s => s['1M'] > 0).length;
  const l1M     = fullScanData.filter(s => s['1M'] < 0).length;
  const multi   = fullScanData.filter(s => s['12M'] > 100).length;

  // Market breadth 1W from summary if available
  const mb1W = summaryData?.market_breadth?.['1W'];
  const adRatio = mb1W ? mb1W.advance_decline_ratio.toFixed(2) : '—';
  const avgRet  = mb1W ? (mb1W.avg_return_pct > 0 ? '+' : '') + mb1W.avg_return_pct.toFixed(2) + '%' : '—';

  el.innerHTML = [
    statCard(total,    'Stocks Scanned', 'col-blue'),
    statCard(g1W,      '1W Gainers',     'col-green'),
    statCard(g1M,      '1M Gainers',     'col-green'),
    statCard(l1M,      '1M Losers',      'col-red'),
    statCard(multi,    '12M > 100%',     'col-purple'),
    statCard(adRatio,  '1W A/D Ratio',   adRatio >= 1 ? 'col-green' : 'col-red'),
    statCard(avgRet,   '1W Avg Return',  avgRet.startsWith('+') ? 'col-green' : 'col-red'),
  ].join('');
}

function statCard(val, label, cls) {
  return `<div class="stat-card">
    <div class="sv ${cls}">${val}</div>
    <div class="sl">${label}</div>
  </div>`;
}

/* ═══════════════════════════════════════════════════════════════
   FULL SCAN TABLE
═══════════════════════════════════════════════════════════════ */
function buildFullScan() {
  document.getElementById('fsBadge').textContent = fullScanData.length;
  if (fullScanData.length === 0) {
    document.getElementById('fsTbody').innerHTML =
      `<tr><td colspan="9" style="text-align:center;padding:40px;color:rgba(255,255,255,0.3);">
        No scan data available. The daily scan runs at 4:45 PM IST (Mon–Fri).
      </td></tr>`;
    return;
  }
  _fsPage = 0;
  fsRender();
}

function fsFilteredData() {
  let d = fullScanData;
  if (_fsFilter)   d = d.filter(s => s.t?.toUpperCase().includes(_fsFilter));
  if (_fsTfFilter) d = d.filter(s => s[_fsTfFilter] != null && s[_fsTfFilter] > 0);
  return [...d].sort((a, b) => {
    const av = a[_fsSortCol] ?? (_fsSortAsc ? Infinity : -Infinity);
    const bv = b[_fsSortCol] ?? (_fsSortAsc ? Infinity : -Infinity);
    if (typeof av === 'string') return _fsSortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    return _fsSortAsc ? av - bv : bv - av;
  });
}

function fsRender() {
  const TFS = ['1W','2W','1M','3M','6M','12M'];
  const data = fsFilteredData();
  const total = data.length;
  const page  = data.slice(_fsPage * FS_PAGE, (_fsPage + 1) * FS_PAGE);

  document.getElementById('fsCount').textContent =
    `Showing ${(_fsPage * FS_PAGE) + 1}–${Math.min((_fsPage+1)*FS_PAGE, total)} of ${total} stocks`;

  // Update sort indicators
  ['t','c','1W','2W','1M','3M','6M','12M'].forEach(col => {
    const el = document.getElementById(`th-${col}`);
    if (el) el.textContent = _fsSortCol === col ? (_fsSortAsc ? '▲' : '▼') : '';
  });

  document.getElementById('fsTbody').innerHTML = page.map((s, i) => {
    const cells = TFS.map(tf => {
      const v = s[tf];
      if (v == null) return `<td class="na">—</td>`;
      const pos = v >= 0;
      const abs = Math.abs(v);
      const weight = abs > 50 ? 'bold-hi' : abs > 10 ? 'bold-md' : '';
      const arrow = pos ? '▲' : '▼';
      return `<td class="${pos ? 'pos' : 'neg'} ${weight}">${arrow} ${abs.toFixed(2)}%</td>`;
    }).join('');

    return `<tr>
      <td class="td-ticker"><a href="https://in.tradingview.com/chart/?symbol=NSE:${s.t}" target="_blank" rel="noopener">${s.t}</a></td>
      <td class="td-price">₹${s.c.toFixed(2)}</td>
      <td class="td-date">${s.d}</td>
      ${cells}
    </tr>`;
  }).join('');

  // Pagination
  const totalPages = Math.ceil(total / FS_PAGE);
  const pag = document.getElementById('fsPagination');
  if (totalPages <= 1) { pag.innerHTML = ''; return; }

  const pages = [];
  pages.push(`<button class="pg-btn" onclick="fsGo(Math.max(0,${_fsPage}-1))">← Prev</button>`);

  const start = Math.max(0, _fsPage - 2);
  const end   = Math.min(totalPages, _fsPage + 4);
  if (start > 0) pages.push(`<button class="pg-btn" onclick="fsGo(0)">1</button><span style="color:rgba(255,255,255,0.3)">…</span>`);
  for (let p = start; p < end; p++) {
    pages.push(`<button class="pg-btn ${p === _fsPage ? 'active' : ''}" onclick="fsGo(${p})">${p+1}</button>`);
  }
  if (end < totalPages) pages.push(`<span style="color:rgba(255,255,255,0.3)">…</span><button class="pg-btn" onclick="fsGo(${totalPages-1})">${totalPages}</button>`);
  pages.push(`<button class="pg-btn" onclick="fsGo(Math.min(${totalPages-1},${_fsPage}+1))">Next →</button>`);

  pag.innerHTML = pages.join('');
}

function fsGo(page) { _fsPage = page; fsRender(); window.scrollTo({top: 200, behavior:'smooth'}); }
function fsSort(col) {
  if (_fsSortCol === col) _fsSortAsc = !_fsSortAsc;
  else { _fsSortCol = col; _fsSortAsc = col === 't'; }
  _fsPage = 0; fsRender();
}
function onFsSearch() { _fsFilter = document.getElementById('fsSearch').value.toUpperCase(); _fsPage = 0; fsRender(); }
function onFsFilter() { _fsTfFilter = document.getElementById('fsTfFilter').value; _fsPage = 0; fsRender(); }

/* ═══════════════════════════════════════════════════════════════
   TOP SETUPS (from backend data + static fallback)
═══════════════════════════════════════════════════════════════ */
function onTfChange(btn) {
  document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentTf = btn.dataset.tf;
  buildSetups(currentTf);
}

function buildSetups(tf) {
  const container = document.getElementById('setupsContent');
  let setups = [];

  // Try live backend data first
  if (summaryData?.top_10_by_timeframe?.[tf]) {
    const stocks = summaryData.top_10_by_timeframe[tf];
    const breadth = summaryData.market_breadth?.[tf];
    setups = stocks.slice(0,5).map((s, i) => buildSetupFromScan(s, tf, i+1, breadth));
  }

  // Fallback to static data.js setups
  if (setups.length === 0) {
    const S = typeof REPORT_DATA !== 'undefined' ? REPORT_DATA : null;
    if (S?.setups) setups = S.setups.map(s => renderStaticSetup(s));
  }

  if (setups.length === 0) {
    container.innerHTML = `<div style="padding:40px;text-align:center;color:rgba(255,255,255,0.4);">No setups available for this timeframe.</div>`;
    return;
  }
  container.innerHTML = setups.join('');
}

function buildSetupFromScan(stock, tf, rank, breadth) {
  const pct = stock[tf] ?? stock[Object.keys(stock).find(k => k !== 'ticker' && k !== 'last_close')] ?? 0;
  const isBreakout = pct > 20;
  const badgeCls = isBreakout ? 'badge-breakout' : 'badge-reversion';
  const badgeLbl = isBreakout ? 'Strong Breakout' : 'Momentum Leader';
  const entry = stock.last_close;
  const sl = (entry * 0.92).toFixed(2);
  const t1 = (entry * 1.08).toFixed(2);
  const t2 = (entry * 1.16).toFixed(2);
  const adNote = breadth ? `Market breadth: ${breadth.advancing} advancing / ${breadth.declining} declining (A/D ${breadth.advance_decline_ratio})` : '';

  return `<div class="setup-card">
    <div class="setup-header">
      <div class="setup-rank">#${rank}</div>
      <div style="flex:1">
        <div class="setup-name">${stock.ticker} <span class="setup-ticker">NSE: ${stock.ticker}</span></div>
        <span class="setup-type-badge ${badgeCls}">${badgeLbl}</span>
      </div>
      <div style="text-align:right">
        <div class="setup-cmp">₹${entry.toFixed(2)}</div>
        <div style="font-size:11px;color:rgba(255,255,255,0.3);">Last Close</div>
        <div style="color:var(--green);font-weight:800;font-size:16px;margin-top:2px;">${pct > 0 ? '+' : ''}${pct.toFixed(2)}% (${tf})</div>
      </div>
    </div>
    <div class="trigger-note">
      ⚡ <strong>${tf} momentum leader</strong> — ranked #${rank} out of ${summaryData?.total_stocks_scanned || '2200+'} NSE stocks.
      ${adNote}
    </div>
    <div class="trade-grid">
      <div class="trade-box-item"><div class="trade-label">Entry Zone</div><div class="trade-val entry-val">₹${entry.toFixed(2)}</div></div>
      <div class="trade-box-item"><div class="trade-label">Stop Loss (8%)</div><div class="trade-val sl-val">₹${sl}</div></div>
      <div class="trade-box-item"><div class="trade-label">Target 1 (+8%)</div><div class="trade-val t1-val">₹${t1}</div></div>
      <div class="trade-box-item"><div class="trade-label">Target 2 (+16%)</div><div class="trade-val t2-val">₹${t2}</div></div>
    </div>
    <div style="display:flex;gap:10px;align-items:center;margin-top:4px;">
      <a href="https://in.tradingview.com/chart/?symbol=NSE:${stock.ticker}" target="_blank" rel="noopener"
         style="font-size:12px;padding:6px 14px;border:1px solid var(--border);border-radius:6px;color:var(--primary);">
        📊 View Chart on TradingView ↗
      </a>
      <span style="font-size:11px;color:rgba(255,255,255,0.2);">⚠️ Educational only. Not investment advice.</span>
    </div>
  </div>`;
}

function renderStaticSetup(s) {
  const rsiColor = s.technical.rsi.value < 40 ? 'bull' : s.technical.rsi.value > 65 ? 'bear' : 'neut';
  return `<div class="setup-card">
    <div class="setup-header">
      <div class="setup-rank">#${s.rank}</div>
      <div style="flex:1">
        <div class="setup-name">${s.name} <span class="setup-ticker">NSE: ${s.ticker}</span></div>
        <div style="margin-top:4px;font-size:12px;color:rgba(255,255,255,0.35);">${s.marketCap}</div>
        <span class="setup-type-badge badge-${s.setupType}">${s.setupLabel}</span>
      </div>
      <div style="text-align:right">
        <div class="setup-cmp">${s.cmp}</div>
        <div style="font-size:11px;color:rgba(255,255,255,0.3);">Current Price</div>
      </div>
    </div>
    <div class="setup-grid">
      <div>
        <div class="setup-section-title">📈 Technical</div>
        <div class="ind-row"><span class="ind-key">RSI (14)</span><span class="ind-val ${rsiColor}">${s.technical.rsi.label}</span></div>
        <div class="ind-row"><span class="ind-key">MACD</span><span class="ind-val ${s.technical.macd.signal === 'bullish' ? 'bull' : 'bear'}">${s.technical.macd.label}</span></div>
        <div class="ind-row"><span class="ind-key">Moving Avgs</span><span class="ind-val" style="font-size:11px;">${s.technical.dma.label}</span></div>
        <div class="ind-row"><span class="ind-key">Volume</span><span class="ind-val ${s.technical.volume.status === 'surge' ? 'bull' : ''}">${s.technical.volume.status.toUpperCase()}</span></div>
        <div class="ind-row"><span class="ind-key">Support</span><span class="ind-val bull">${s.technical.support}</span></div>
        <div class="ind-row"><span class="ind-key">Resistance</span><span class="ind-val bear">${s.technical.resistance}</span></div>
      </div>
      <div>
        <div class="setup-section-title">🔬 Fundamental</div>
        <div class="ind-row"><span class="ind-key">P/E</span><span class="ind-val">${s.fundamental.pe}</span></div>
        <div class="ind-row"><span class="ind-key">Debt/Equity</span><span class="ind-val">${s.fundamental.de}</span></div>
        <div class="ind-row"><span class="ind-key">Promoter %</span><span class="ind-val">${s.fundamental.promoterHolding}</span></div>
        <div class="ind-row"><span class="ind-key">Revenue Growth</span><span class="ind-val bull">${s.fundamental.salesGrowth}</span></div>
        <div class="ind-row"><span class="ind-key">Profit Growth</span><span class="ind-val bull">${s.fundamental.profitGrowth}</span></div>
      </div>
    </div>
    <div class="trigger-note" style="margin-top:14px;">⚡ ${s.trigger}</div>
    <div class="trade-grid" style="margin-top:14px;">
      <div class="trade-box-item"><div class="trade-label">Entry Zone</div><div class="trade-val entry-val">₹${s.trade.entryLow}–${s.trade.entryHigh}</div></div>
      <div class="trade-box-item"><div class="trade-label">Stop Loss</div><div class="trade-val sl-val">₹${s.trade.sl} (${s.trade.slPct})</div></div>
      <div class="trade-box-item"><div class="trade-label">Target 1</div><div class="trade-val t1-val">₹${s.trade.t1} (${s.trade.t1Pct})</div></div>
      <div class="trade-box-item"><div class="trade-label">Target 2</div><div class="trade-val t2-val">₹${s.trade.t2} (${s.trade.t2Pct})</div></div>
    </div>
    <div style="display:flex;gap:10px;margin-top:10px;align-items:center;">
      <a href="${s.chartLink}" target="_blank" rel="noopener" style="font-size:12px;padding:6px 14px;border:1px solid var(--border);border-radius:6px;color:var(--primary);">📊 View Chart ↗</a>
      <span style="font-size:11px;color:rgba(255,255,255,0.2);">⚠️ Educational only. R/R: ${s.trade.rrRatio}</span>
    </div>
  </div>`;
}

/* ═══════════════════════════════════════════════════════════════
   MARKET SNAPSHOT
═══════════════════════════════════════════════════════════════ */
function buildMarket(S) {
  const el = document.getElementById('marketContent');
  if (!S?.market) {
    el.innerHTML = `<div class="card" style="color:rgba(255,255,255,0.4);">Market snapshot data not available.</div>`;
    return;
  }
  const m = S.market;

  // Inject live breadth if we have it
  let biasNote = m.biasNote;
  let bias = m.bias, biasCls = m.biasClass;
  if (summaryData?.market_breadth?.['1W']) {
    const mb = summaryData.market_breadth['1W'];
    bias = mb.advance_decline_ratio > 1 ? 'Bullish' : 'Bearish';
    biasCls = mb.advance_decline_ratio > 1 ? 'bull' : 'bear';
    biasNote = `1W Market Breadth: ${mb.advancing} Advancing vs ${mb.declining} Declining. A/D Ratio: ${mb.advance_decline_ratio}. Avg return: ${mb.avg_return_pct > 0 ? '+' : ''}${mb.avg_return_pct}%.`;
  }

  const idxHtml = m.indices.map(idx => `
    <div class="index-card">
      <div class="ic-label">${idx.label}</div>
      <div class="ic-value">${idx.value}</div>
      <div class="ic-change ${idx.trend === 'bullish' ? 'up' : idx.trend === 'bearish' ? 'dn' : 'flat'}">
        ${idx.trend === 'bullish' ? '▲' : '▼'} ${idx.change} (${idx.pts})
      </div>
      <div class="ic-sub">Weekly: ${idx.weekly} · ${idx.sub}</div>
    </div>`).join('');

  const evHtml = m.events.map(ev => `
    <div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
      <span style="font-size:12px;font-family:var(--mono);color:rgba(255,255,255,0.4);white-space:nowrap;">${ev.date}</span>
      <span style="background:rgba(61,142,244,0.15);color:var(--blue);font-size:10px;font-weight:700;padding:2px 7px;border-radius:4px;white-space:nowrap;">${ev.tag.toUpperCase()}</span>
      <span style="font-size:13px;color:rgba(255,255,255,0.65);">${ev.desc}</span>
    </div>`).join('');

  el.innerHTML = `
    <div class="index-grid">${idxHtml}</div>
    <div class="card" style="display:flex;gap:16px;align-items:flex-start;margin-bottom:16px;">
      <div style="flex:0 0 auto;">
        <div style="font-size:11px;color:rgba(255,255,255,0.4);margin-bottom:4px;">Market Bias</div>
        <div style="font-size:24px;font-weight:800;" class="${biasCls}">${bias}</div>
      </div>
      <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.7;border-left:1px solid var(--border);padding-left:16px;">${biasNote}</div>
    </div>
    <div class="card">
      <div style="font-size:15px;font-weight:600;margin-bottom:14px;">📅 Key Events This Week</div>
      ${evHtml}
    </div>
    <div class="card" style="display:flex;gap:12px;flex-wrap:wrap;">
      <strong style="font-size:13px;">🏆 Top Sectors:</strong>
      ${m.topSectors.map(s => `<span style="background:rgba(16,245,168,0.1);color:var(--green);padding:4px 14px;border-radius:6px;font-size:13px;">${s}</span>`).join('')}
    </div>`;
}

/* ═══════════════════════════════════════════════════════════════
   WATCHLIST
═══════════════════════════════════════════════════════════════ */
function buildWatchlist(S) {
  const el = document.getElementById('watchlistContent');
  if (!S?.watchlist) { el.innerHTML = `<div class="card" style="color:rgba(255,255,255,0.4);">Watchlist not available.</div>`; return; }

  const rows = S.watchlist.map(w => `
    <div class="wl-row">
      <div><strong>${w.name}</strong><div style="font-size:11px;color:rgba(255,255,255,0.35);">${w.ticker}</div></div>
      <div style="font-family:var(--mono);">${w.cmp}</div>
      <div class="readiness-${w.readiness}">${w.readiness.toUpperCase()}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.5);">${w.watchLevel}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.6);">${w.trigger}</div>
    </div>`).join('');

  el.innerHTML = `
    <div class="wl-table">
      <div class="wl-row wl-header">
        <div>Stock</div><div>CMP</div><div>Status</div><div>Watch Level</div><div>Entry Trigger</div>
      </div>
      ${rows}
    </div>`;
}

/* ═══════════════════════════════════════════════════════════════
   SECTOR HEATMAP
═══════════════════════════════════════════════════════════════ */
function buildHeatmap(S) {
  const el = document.getElementById('heatmapContent');
  if (!S?.sectors) { el.innerHTML = `<div class="card" style="color:rgba(255,255,255,0.4);">Heatmap data not available.</div>`; return; }

  const sorted = [...S.sectors].sort((a,b) => parseFloat(b.change) - parseFloat(a.change));
  const cells = sorted.map(s => {
    const pct = parseFloat(s.change);
    const cls = pct > 2 ? 'hm-sb' : pct > 0.5 ? 'hm-b' : pct > 0 ? 'hm-slb' :
                pct > -1 ? 'hm-f' : pct > -2 ? 'hm-sbe' : pct > -3 ? 'hm-be' : 'hm-sbe2';
    return `<div class="hm-cell ${cls}">
      <div class="hm-name">${s.name}</div>
      <div class="hm-idx">${s.index}</div>
      <div class="hm-chng">${s.change}</div>
      <div class="hm-vol">Vol: ${s.vol}</div>
    </div>`;
  }).join('');

  el.innerHTML = `<div class="heatmap-grid">${cells}</div>`;
}

/* ═══════════════════════════════════════════════════════════════
   RISK DASHBOARD
═══════════════════════════════════════════════════════════════ */
function buildRisk(S) {
  const el = document.getElementById('riskContent');
  if (!S?.risk) { el.innerHTML = `<div class="card" style="color:rgba(255,255,255,0.4);">Risk data not available.</div>`; return; }
  const r = S.risk;
  const vixPct = Math.min((parseFloat(r.vix.value) / 35) * 100, 100);

  const macroRows = r.macro.map(m => `
    <tr>
      <td>${m.indicator}</td>
      <td style="font-weight:700;font-family:var(--mono);">${m.value}</td>
      <td style="font-size:12px;color:${m.impactClass === 'bullish' ? 'var(--green)' : m.impactClass === 'bearish' ? 'var(--red)' : 'var(--amber)'};">${m.impact}</td>
    </tr>`).join('');

  const evHtml = r.upcomingEvents.map(e =>
    `<li style="padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:13px;color:rgba(255,255,255,0.6);">${e}</li>`
  ).join('');

  el.innerHTML = `
    <div class="risk-grid">
      <div class="risk-card">
        <div class="risk-label">India VIX</div>
        <div class="risk-val" style="color:var(--amber);">${r.vix.value}</div>
        <div style="font-size:12px;color:rgba(255,255,255,0.35);">Status: ${r.vix.status}</div>
        <div class="vix-track"><div class="vix-needle" id="vixNeedle" data-pct="${vixPct}" style="left:${vixPct}%"></div></div>
        <div style="display:flex;justify-content:space-between;font-size:10px;color:rgba(255,255,255,0.25);margin-top:2px;"><span>0</span><span>17</span><span>25</span><span>35+</span></div>
      </div>
      <div class="risk-card">
        <div class="risk-label">Nifty 50</div>
        <div class="risk-val" style="color:var(--blue);">${r.niftyCurrent}</div>
        <div style="font-size:12px;color:rgba(255,255,255,0.35);">Support: ${r.niftySupport[0]} · Resistance: ${r.niftyResistance[0]}</div>
      </div>
      <div class="risk-card">
        <div class="risk-label">Overall Risk</div>
        <div class="risk-val" style="color:${r.overallRisk.level === 'Low' ? 'var(--green)' : r.overallRisk.level === 'High' ? 'var(--red)' : 'var(--amber)'};">${r.overallRisk.level}</div>
        <div style="font-size:12px;color:rgba(255,255,255,0.35);">Reduce sizes in high-risk environment.</div>
      </div>
    </div>
    <div class="card" style="margin-bottom:16px;">
      <div style="font-size:14px;font-weight:600;margin-bottom:12px;">📊 Macro Indicators</div>
      <table class="macro-table">
        <thead><tr><th>Indicator</th><th>Value</th><th>Market Impact</th></tr></thead>
        <tbody>${macroRows}</tbody>
      </table>
    </div>
    <div class="card">
      <div style="font-size:14px;font-weight:600;margin-bottom:12px;">📅 Key Events This Week</div>
      <ul style="list-style:none;">${evHtml}</ul>
    </div>`;
}

/* ═══════════════════════════════════════════════════════════════
   NEWS
═══════════════════════════════════════════════════════════════ */
function buildNews() {
  const el = document.getElementById('newsContent');
  if (!newsData || newsData.length === 0) {
    el.innerHTML = `<div class="card" style="color:rgba(255,255,255,0.4);">No news data available.</div>`;
    return;
  }
  el.innerHTML = newsData.map(item => `
    <div class="news-item">
      <div class="news-source">[${item.source}]</div>
      <div class="news-title">
        <a href="${item.link}" target="_blank" rel="noopener" style="color:#e6edf3;">${item.title}</a>
      </div>
      <div class="news-time">${item.time}</div>
    </div>`).join('');
}

/* ═══════════════════════════════════════════════════════════════
   ANIMATIONS
═══════════════════════════════════════════════════════════════ */
function animateNeedles() {
  const needle = document.getElementById('vixNeedle');
  if (!needle) return;
  const target = needle.dataset.pct + '%';
  needle.style.left = '50%';
  requestAnimationFrame(() => setTimeout(() => { needle.style.left = target; }, 50));
}
