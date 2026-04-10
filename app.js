/**
 * MarketPulse India — Main App
 * 5 tabs: Opportunities (engine), Top Movers, Full Scan, News, About
 * Auto-loads on page open. Zero maintenance. GitHub Pages hosted.
 */

/* ═══════════════════════════════════════════════════════════════
   GLOBALS
═══════════════════════════════════════════════════════════════ */
let summaryData    = null;   // latest_scan_summary.json
let fullScanData   = [];     // full_summary.json → stocks[]
let fundamentals   = {};     // fundamentals.json → keyed by symbol
let newsData       = [];     // daily_news.json
let opportunitiesData = [];  // opportunities.json → opportunities[]
let currentTf      = '1M';

// Full Scan table state
let _fsSortCol = '1M', _fsSortAsc = false, _fsFilter = '', _fsTfFilter = '', _fsMcapFilter = '', _fsPage = 0;
const FS_PAGE = 100;

// Top Movers filter state
let _tmSearch = '', _tmSector = '', _tmPe = '', _tmMcap = '', _tmPage = 0;
const TM_PAGE = 40;

// Opportunity filter state
let _oppSearch = '', _oppSignal = '', _oppMinScore = 50, _oppSector = '';

const TFS = ['1W','2W','1M','3M','6M','12M'];

/* ═══════════════════════════════════════════════════════════════
   BOOT
═══════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initTabs();
  loadEverything();
});

/* ═══════════════════════════════════════════════════════════════
   CLOCK
═══════════════════════════════════════════════════════════════ */
function initClock() {
  const tick = () => {
    const ist = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
    const p = n => String(n).padStart(2,'0');
    document.getElementById('clock').textContent = `${p(ist.getHours())}:${p(ist.getMinutes())}:${p(ist.getSeconds())} IST`;
  };
  tick(); setInterval(tick, 1000);
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
   LOAD ALL DATA IN PARALLEL
═══════════════════════════════════════════════════════════════ */
async function loadEverything() {
  try {
    const [summRes, fullRes, fundRes, newsRes, oppRes] = await Promise.allSettled([
      fetch('scan_results/latest_scan_summary.json'),
      fetch('scan_results/full_summary.json'),
      fetch('scan_results/fundamentals.json'),
      fetch('scan_results/daily_news.json'),
      fetch('scan_results/opportunities.json'),
    ]);

    // Parse summary
    if (summRes.status === 'fulfilled' && summRes.value.ok) {
      summaryData = await summRes.value.json();
    }

    // Parse full scan
    if (fullRes.status === 'fulfilled' && fullRes.value.ok) {
      const fj = await fullRes.value.json();
      fullScanData = fj.stocks || [];
      if (summaryData && fj.generated) summaryData.scan_date = fj.generated;
    }

    // Parse fundamentals → key by symbol for O(1) lookup
    if (fundRes.status === 'fulfilled' && fundRes.value.ok) {
      const fj = await fundRes.value.json();
      (fj.stocks || []).forEach(s => { if (s.s) fundamentals[s.s] = s; });
      console.log(`✅ Loaded fundamentals for ${Object.keys(fundamentals).length} stocks`);
    } else {
      console.warn('⚠️ fundamentals.json not available — Top Movers will show without fundamental data');
    }

    // Parse news
    if (newsRes.status === 'fulfilled' && newsRes.value.ok) {
      newsData = await newsRes.value.json();
    }

    // Parse opportunities
    if (oppRes && oppRes.status === 'fulfilled' && oppRes.value.ok) {
      const oj = await oppRes.value.json();
      opportunitiesData = oj.opportunities || [];
    }

  } catch (err) {
    // Network failure — show inline warning banner; AI Picks still works (static data)
    console.warn('Scan data fetch failed:', err.message);
    document.getElementById('errorScreen').style.display = 'flex';
  } finally {
    // Always reveal the dashboard so static tabs are accessible
    buildDashboard();
    document.getElementById('loadScreen').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';
  }
}

/* ═══════════════════════════════════════════════════════════════
   DASHBOARD ORCHESTRATOR
═══════════════════════════════════════════════════════════════ */
function buildDashboard() {
  const scanDate   = summaryData?.scan_date || '—';
  const stockCount = fullScanData.length || summaryData?.total_stocks_scanned || '—';
  document.getElementById('hScanDate').textContent   = scanDate;
  document.getElementById('hStockCount').textContent  = stockCount;
  document.getElementById('footerDate').textContent   = scanDate;

  buildStatsRow();
  buildOpportunities();
  buildTopMovers();
  buildFullScan();
  buildNews();
  buildAIPicksTab(); // AI Picks uses static data — always safe to call
}

/* ═══════════════════════════════════════════════════════════════
   STATS ROW
═══════════════════════════════════════════════════════════════ */
function buildStatsRow() {
  const el = document.getElementById('statsRow');
  const total = fullScanData.length;
  const g1W   = fullScanData.filter(s => s['1W'] > 0).length;
  const g1M   = fullScanData.filter(s => s['1M'] > 0).length;
  const l1M   = fullScanData.filter(s => s['1M'] < 0).length;
  const multi = fullScanData.filter(s => s['12M'] > 100).length;
  const oppCount = opportunitiesData.length;

  const mb1W = summaryData?.market_breadth?.['1W'];
  const adRatio = mb1W ? mb1W.advance_decline_ratio.toFixed(1) : '—';

  const sc = (v, l, c) => `<div class="stat-card"><div class="sv ${c}">${v}</div><div class="sl">${l}</div></div>`;
  el.innerHTML = [
    sc(total,     'Stocks Scanned', 'col-blue'),
    sc(oppCount,  '🎯 Opportunities','col-emerald'),
    sc(g1W,       '1W Gainers',     'col-green'),
    sc(g1M,       '1M Gainers',     'col-green'),
    sc(l1M,       '1M Losers',      'col-red'),
    sc(multi,     '12M > 100%',     'col-purple'),
    sc(adRatio,   '1W A/D Ratio',   'col-amber'),
  ].join('');
}

/* ═══════════════════════════════════════════════════════════════
   TOP MOVERS — All NSE Stocks
═══════════════════════════════════════════════════════════════ */
function buildTopMovers() {
  // All stocks, sorted by 1M performance by default
  const movers = [...fullScanData].sort((a, b) => (b['1M'] || 0) - (a['1M'] || 0));

  document.getElementById('moversBadge').textContent = movers.length;
  window._moversData = movers;

  // Populate sector dropdown
  const sectors = new Set();
  movers.forEach(s => { const f = fundamentals[s.t]; if (f?.sector) sectors.add(f.sector); });
  const selSector = document.getElementById('tmSector');
  [...sectors].sort().forEach(sec => {
    const opt = document.createElement('option');
    opt.value = sec; opt.textContent = sec;
    selSector.appendChild(opt);
  });

  renderTopMovers();
}

function renderTopMovers() {
  let data = window._moversData || [];

  // Apply filters
  if (_tmSearch) data = data.filter(s => s.t?.toUpperCase().includes(_tmSearch));
  if (_tmSector) data = data.filter(s => fundamentals[s.t]?.sector === _tmSector);
  if (_tmPe) {
    data = data.filter(s => {
      const pe = fundamentals[s.t]?.pe;
      if (!pe) return false;
      if (_tmPe === 'value') return pe < 15;
      if (_tmPe === 'mid')   return pe >= 15 && pe <= 40;
      if (_tmPe === 'high')  return pe > 40;
      return true;
    });
  }
  if (_tmMcap) {
    data = data.filter(s => (s.m || 'S') === _tmMcap);
  }

  const total = data.length;
  const page = data.slice(_tmPage * TM_PAGE, (_tmPage + 1) * TM_PAGE);

  document.getElementById('tmCount').textContent = `Showing ${_tmPage * TM_PAGE + 1}–${Math.min((_tmPage+1)*TM_PAGE, total)} of ${total}`;

  const grid = document.getElementById('moversGrid');
  if (data.length === 0) {
    grid.innerHTML = `<div style="padding:40px;text-align:center;color:rgba(255,255,255,0.3);grid-column:1/-1;">No stocks match your filters.</div>`;
    document.getElementById('tmPagination').innerHTML = '';
    return;
  }

  grid.innerHTML = page.map((s, i) => {
    const f  = fundamentals[s.t] || {};
    const pct1M  = s['1M'];
    const pct12M = s['12M'];
    const isUp = (pct1M || 0) >= 0;

    // Auto-tags
    const tags = [];
    if (f.pe && f.pe < 15) tags.push('<span class="mc-tag tag-value">Value</span>');
    if (f.pe && f.pe > 50) tags.push('<span class="mc-tag tag-highpe">High P/E</span>');
    if (f.dy && f.dy > 3) tags.push('<span class="mc-tag tag-income">Income</span>');
    if (pct12M && pct12M > 100) tags.push('<span class="mc-tag tag-multi">Multibagger</span>');
    if (s['1W'] && s['1W'] > 20) tags.push('<span class="mc-tag tag-breakout">Breakout</span>');

    // Fundamental cells
    const fv = (val, suffix='') => val != null ? `${val}${suffix}` : '—';
    const fvCls = (val) => val != null ? '' : 'na';
    const mcapStr = f.mcap ? (f.mcap >= 10000 ? `₹${(f.mcap/1000).toFixed(1)}K Cr` : `₹${f.mcap.toFixed(0)} Cr`) : '—';

    // Display name
    const displayName = f.name || s.t;

    // TF cells
    const tfCells = TFS.map(tf => {
      const v = s[tf];
      if (v == null) return `<div class="mc-tf-cell na">—</div>`;
      return `<div class="mc-tf-cell ${v >= 0 ? 'up' : 'dn'}">${v >= 0 ? '+' : ''}${v.toFixed(1)}%</div>`;
    }).join('');

    return `<div class="mover-card">
      <div class="mc-glow ${isUp ? 'up' : 'dn'}"></div>
      <div class="mc-top">
        <div class="mc-rank">#${(_tmPage * TM_PAGE) + i + 1}</div>
        <div class="mc-info">
          <div class="mc-name"><a href="https://in.tradingview.com/chart/?symbol=NSE:${s.t}" target="_blank" rel="noopener">${s.t}</a></div>
          <div class="mc-sub">
            ${f.sector ? `<span class="mc-sector-pill">${f.sector}</span>` : ''}
            <span>${mcapStr}</span>
            <span style="color:rgba(255,255,255,0.15);">·</span>
            <span>${f.ind || '—'}</span>
          </div>
        </div>
        <div class="mc-price">
          <div class="mc-cmp">₹${s.c.toFixed(2)}</div>
          ${pct1M != null ? `<div class="mc-pct ${pct1M >= 0 ? 'up' : 'dn'}">${pct1M >= 0 ? '▲' : '▼'} ${Math.abs(pct1M).toFixed(2)}% <span style="font-size:10px;opacity:0.5;">(1M)</span></div>` : ''}
        </div>
      </div>
      ${tags.length ? `<div class="mc-tags">${tags.join('')}</div>` : ''}
      <div class="mc-fundgrid">
        <div class="mc-fund-item"><div class="mc-fund-label">P/E</div><div class="mc-fund-val ${fvCls(f.pe)}">${fv(f.pe, 'x')}</div></div>
        <div class="mc-fund-item"><div class="mc-fund-label">EPS</div><div class="mc-fund-val ${fvCls(f.eps)}">${fv(f.eps ? `₹${f.eps}` : null)}</div></div>
        <div class="mc-fund-item"><div class="mc-fund-label">Book Val</div><div class="mc-fund-val ${fvCls(f.bv)}">${fv(f.bv ? `₹${f.bv}` : null)}</div></div>
        <div class="mc-fund-item"><div class="mc-fund-label">Div Yield</div><div class="mc-fund-val ${fvCls(f.dy)}">${fv(f.dy, '%')}</div></div>
      </div>
      <div class="mc-tf-header">${TFS.map(tf => `<div class="mc-tf-h">${tf}</div>`).join('')}</div>
      <div class="mc-tfs">${tfCells}</div>
      <div class="mc-footer">
        <a class="mc-chart-link" href="https://in.tradingview.com/chart/?symbol=NSE:${s.t}" target="_blank" rel="noopener">📊 Chart ↗</a>
        ${f['52l'] && f['52h'] ? `<span class="mc-52w">52W: ₹${f['52l']} — ₹${f['52h']}</span>` : ''}
      </div>
    </div>`;
  }).join('');

  // Pagination for Top Movers
  const totalPages = Math.ceil(total / TM_PAGE);
  const pag = document.getElementById('tmPagination');
  if (totalPages <= 1) { pag.innerHTML = ''; return; }
  const pages = [];
  pages.push(`<button class="pg-btn" onclick="tmGo(Math.max(0,${_tmPage}-1))">← Prev</button>`);
  const start = Math.max(0, _tmPage - 2), end = Math.min(totalPages, _tmPage + 5);
  if (start > 0) pages.push(`<button class="pg-btn" onclick="tmGo(0)">1</button><span style="color:rgba(255,255,255,0.2)">…</span>`);
  for (let p = start; p < end; p++) pages.push(`<button class="pg-btn ${p === _tmPage ? 'active' : ''}" onclick="tmGo(${p})">${p+1}</button>`);
  if (end < totalPages) pages.push(`<span style="color:rgba(255,255,255,0.2)">…</span><button class="pg-btn" onclick="tmGo(${totalPages-1})">${totalPages}</button>`);
  pages.push(`<button class="pg-btn" onclick="tmGo(Math.min(${totalPages-1},${_tmPage}+1))">Next →</button>`);
  pag.innerHTML = pages.join('');
}

function tmGo(page) { _tmPage = page; renderTopMovers(); window.scrollTo({top: 200, behavior:'smooth'}); }

function onTmSearch() { _tmSearch = document.getElementById('tmSearch').value.toUpperCase(); _tmPage = 0; renderTopMovers(); }
function onTmSector() { _tmSector = document.getElementById('tmSector').value; _tmPage = 0; renderTopMovers(); }
function onTmPe()     { _tmPe     = document.getElementById('tmPe').value;     _tmPage = 0; renderTopMovers(); }
function onTmMcap()   { _tmMcap   = document.getElementById('tmMcap').value;   _tmPage = 0; renderTopMovers(); }

/* ═══════════════════════════════════════════════════════════════
   FULL SCAN TABLE
═══════════════════════════════════════════════════════════════ */
function buildFullScan() {
  document.getElementById('fsBadge').textContent = fullScanData.length;
  if (!fullScanData.length) {
    document.getElementById('fsTbody').innerHTML = `<tr><td colspan="9" style="text-align:center;padding:40px;color:rgba(255,255,255,0.25);">No scan data available. The daily scan runs at 4:45 PM IST (Mon–Fri).</td></tr>`;
    return;
  }
  _fsPage = 0;
  fsRender();
}

function fsFilteredData() {
  let d = fullScanData;
  if (_fsFilter)   d = d.filter(s => s.t?.toUpperCase().includes(_fsFilter));
  if (_fsTfFilter) d = d.filter(s => s[_fsTfFilter] != null && s[_fsTfFilter] > 0);
  if (_fsMcapFilter) d = d.filter(s => (s.m || 'S') === _fsMcapFilter);
  return [...d].sort((a, b) => {
    const av = a[_fsSortCol] ?? (_fsSortAsc ? Infinity : -Infinity);
    const bv = b[_fsSortCol] ?? (_fsSortAsc ? Infinity : -Infinity);
    if (typeof av === 'string') return _fsSortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    return _fsSortAsc ? av - bv : bv - av;
  });
}

function fsRender() {
  const data = fsFilteredData();
  const total = data.length;
  const page  = data.slice(_fsPage * FS_PAGE, (_fsPage + 1) * FS_PAGE);

  document.getElementById('fsCount').textContent = `Showing ${(_fsPage * FS_PAGE) + 1}–${Math.min((_fsPage+1)*FS_PAGE, total)} of ${total}`;

  ['t','c','1W','2W','1M','3M','6M','12M'].forEach(col => {
    const el = document.getElementById(`th-${col}`);
    if (el) el.textContent = _fsSortCol === col ? (_fsSortAsc ? '▲' : '▼') : '';
  });

  document.getElementById('fsTbody').innerHTML = page.map(s => {
    const cells = TFS.map(tf => {
      const v = s[tf];
      if (v == null) return `<td class="na">—</td>`;
      const abs = Math.abs(v);
      const w = abs > 50 ? 'bold-hi' : abs > 10 ? 'bold-md' : '';
      return `<td class="${v >= 0 ? 'pos' : 'neg'} ${w}">${v >= 0 ? '▲' : '▼'} ${abs.toFixed(2)}%</td>`;
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
  const start = Math.max(0, _fsPage - 2), end = Math.min(totalPages, _fsPage + 5);
  if (start > 0) pages.push(`<button class="pg-btn" onclick="fsGo(0)">1</button><span style="color:rgba(255,255,255,0.2)">…</span>`);
  for (let p = start; p < end; p++) pages.push(`<button class="pg-btn ${p === _fsPage ? 'active' : ''}" onclick="fsGo(${p})">${p+1}</button>`);
  if (end < totalPages) pages.push(`<span style="color:rgba(255,255,255,0.2)">…</span><button class="pg-btn" onclick="fsGo(${totalPages-1})">${totalPages}</button>`);
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
function onFsMcap()   { _fsMcapFilter = document.getElementById('fsMcapFilter').value; _fsPage = 0; fsRender(); }

/* ═══════════════════════════════════════════════════════════════
   NEWS
═══════════════════════════════════════════════════════════════ */
function buildNews() {
  const el = document.getElementById('newsContent');
  if (!newsData || !newsData.length) {
    el.innerHTML = `<div style="padding:40px;text-align:center;color:rgba(255,255,255,0.25);">No news data available.</div>`;
    return;
  }
  el.innerHTML = newsData.map(item => `
    <div class="news-item">
      <div class="news-source">[${item.source}]</div>
      <div class="news-title"><a href="${item.link}" target="_blank" rel="noopener">${item.title}</a></div>
      <div class="news-time">${item.time}</div>
    </div>`).join('');
}

/* ═══════════════════════════════════════════════════════════════
   OPPORTUNITIES TAB
═══════════════════════════════════════════════════════════════ */
function buildOpportunities() {
  document.getElementById('oppBadge').textContent = opportunitiesData.length;

  // Populate sector filter
  const sectors = new Set();
  opportunitiesData.forEach(o => { if (o.fundamental?.sector) sectors.add(o.fundamental.sector); });
  const selSec = document.getElementById('oppSector');
  [...sectors].sort().forEach(sec => {
    const opt = document.createElement('option');
    opt.value = sec; opt.textContent = sec;
    selSec.appendChild(opt);
  });

  // Set initial score filter from the select
  _oppMinScore = parseInt(document.getElementById('oppMinScore').value) || 50;

  renderOpportunities();
}

function renderOpportunities() {
  let data = opportunitiesData;

  // Search
  if (_oppSearch) data = data.filter(o => o.ticker.includes(_oppSearch));

  // Signal filter
  if (_oppSignal) data = data.filter(o => (o.signals || []).includes(_oppSignal));

  // Score threshold
  if (_oppMinScore > 0) data = data.filter(o => o.score >= _oppMinScore);

  // Sector filter
  if (_oppSector) data = data.filter(o => o.fundamental?.sector === _oppSector);

  document.getElementById('oppCount').textContent = `${data.length} opportunities`;

  const grid = document.getElementById('oppGrid');

  if (!data.length) {
    grid.innerHTML = `<div class="opp-empty" style="grid-column:1/-1">
      <div class="oe-icon">🎯</div>
      <p>No opportunities match your filters.<br>Try lowering the score threshold or selecting a different signal.</p>
    </div>`;
    return;
  }

  grid.innerHTML = data.map(opp => buildOppCard(opp)).join('');

  // Animate score rings after render
  requestAnimationFrame(() => {
    grid.querySelectorAll('.score-ring-fg').forEach(el => {
      const score = parseFloat(el.dataset.score);
      const r = 26;
      const circ = 2 * Math.PI * r;
      el.style.strokeDasharray = circ;
      el.style.strokeDashoffset = circ - (score / 100) * circ;
    });
  });
}

function buildOppCard(opp) {
  const score  = opp.score || 0;
  const f      = opp.fundamental || {};
  const ind    = opp.indicators  || {};
  const signals = opp.signals || [];

  // Score ring color (green=high, amber=mid, blue=low)
  const ringColor = score >= 75 ? 'var(--emerald)' : score >= 50 ? 'var(--amber)' : 'var(--blue)';
  const r = 26, circ = 2 * Math.PI * r;

  // Signal chips
  const signalMap = {
    '52W_BREAKOUT': ['sig-breakout', '📈 52W Breakout'],
    'VOLUME_SPIKE': ['sig-volume',   '📊 Volume Spike'],
    'EMA_MOMENTUM':['sig-momentum', '🚀 EMA Momentum'],
    'HIGH_VOLUME': ['sig-highvol',  '🔥 High Volume'],
  };
  const chips = signals.map(s => {
    const [cls, label] = signalMap[s] || ['sig-momentum', s];
    return `<span class="signal-chip ${cls}">${label}</span>`;
  }).join('');

  // Indicator cells
  const iv = (v, suffix='', decimals=1) =>
    v != null ? `${parseFloat(v).toFixed(decimals)}${suffix}` : '—';
  const ivCls = v => v != null ? '' : 'na';

  const indItems = [
    { lbl: 'RSI (14)',   val: ind.rsi_14,      suffix: '', dec: 1 },
    { lbl: 'Vol Ratio',  val: ind.volume_ratio, suffix: '×', dec: 1 },
    { lbl: '1M Return',  val: ind.return_1m,    suffix: '%', dec: 1 },
    { lbl: 'EMA 9',      val: ind.ema_9,        suffix: '', dec: 0 },
    { lbl: 'EMA 21',     val: ind.ema_21,       suffix: '', dec: 0 },
    { lbl: '52W High%',  val: ind.pct_from_52w_high != null ? -ind.pct_from_52w_high : null, suffix: '%', dec: 1 },
  ].map(it => `
    <div class="opp-ind-item">
      <div class="opp-ind-lbl">${it.lbl}</div>
      <div class="opp-ind-val ${ivCls(it.val)}">${iv(it.val, it.suffix, it.dec)}</div>
    </div>`).join('');

  // Fundamentals row
  const mcapStr = f.mcap_cr ? (f.mcap_cr >= 10000 ? `₹${(f.mcap_cr/1000).toFixed(1)}K Cr` : `₹${Math.round(f.mcap_cr)} Cr`) : null;
  const funds = [
    mcapStr   ? `<span class="opp-fund-item">MCap <strong>${mcapStr}</strong></span>` : '',
    f.pe      ? `<span class="opp-fund-item">P/E <strong>${f.pe}x</strong></span>` : '',
    f.sector  ? `<span class="opp-fund-item">Sector <strong>${f.sector}</strong></span>` : '',
  ].filter(Boolean).join('');

  const displayName = (f.name && f.name !== opp.ticker) ? f.name : opp.ticker;
  const price = ind.price ? `₹${parseFloat(ind.price).toFixed(2)}` : '—';

  return `<div class="opp-card">
    <div class="opp-header">
      <div class="score-ring-wrap">
        <svg class="score-ring-svg" viewBox="0 0 60 60">
          <circle class="score-ring-bg" cx="30" cy="30" r="${r}"/>
          <circle class="score-ring-fg" cx="30" cy="30" r="${r}"
            data-score="${score}"
            stroke="${ringColor}"
            style="stroke-dasharray:${circ};stroke-dashoffset:${circ}"/>
        </svg>
        <div class="score-ring-text">
          <span class="score-val" style="color:${ringColor}">${score}</span>
          <span class="score-lbl">SCORE</span>
        </div>
      </div>
      <div class="opp-meta">
        <div class="opp-rank">#${opp.rank} · ${price}</div>
        <div class="opp-name">
          <a href="https://in.tradingview.com/chart/?symbol=NSE:${opp.ticker}" target="_blank" rel="noopener">${opp.ticker}</a>
        </div>
        <div class="opp-sector">${displayName !== opp.ticker ? displayName : (f.sector || '')}</div>
      </div>
    </div>
    <div class="signal-chips">${chips}</div>
    <div class="opp-indicators">${indItems}</div>
    ${funds ? `<div class="opp-funds">${funds}</div>` : ''}
    <div class="opp-footer">
      <a class="opp-chart-link" href="https://in.tradingview.com/chart/?symbol=NSE:${opp.ticker}" target="_blank" rel="noopener">📊 Chart ↗</a>
      ${f['52h'] && f['52l'] ? `<span style="font-size:10px;color:rgba(255,255,255,0.2);margin-left:auto;">52W: ₹${f['52l']} – ₹${f['52h']}</span>` : ''}
    </div>
  </div>`;
}

function onOppSearch() {
  _oppSearch = document.getElementById('oppSearch').value.toUpperCase().trim();
  renderOpportunities();
}
function onOppFilter() {
  _oppMinScore = parseInt(document.getElementById('oppMinScore').value) || 0;
  _oppSector   = document.getElementById('oppSector').value;
  renderOpportunities();
}
function onOppChip(btn) {
  document.querySelectorAll('#oppSignalChips .chip').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  _oppSignal = btn.dataset.signal;
  renderOpportunities();
}

/* ═══════════════════════════════════════════════════════════════
   AI PICKS TAB — Static/Mock Data + Renderer
   Structure designed for easy backend integration later:
   replace AI_PICKS_DATA with an API fetch in loadEverything()
═══════════════════════════════════════════════════════════════ */

const AI_PICKS_DATA = [
  {
    ticker: 'RELIANCE',
    name: 'Reliance Industries Ltd.',
    price: '₹2,847.60',
    recommendation: 'buy',
    trend: 'up',
    trendLabel: '↑ Uptrend',
    horizon: 'Medium Term · 2 Months',
    confidence: 82,
    reasons: [
      'Price above 200 DMA — sustained structural uptrend',
      'Strong volume breakout on Friday\'s session (2.4× avg vol)',
      'Momentum positive: 3-month return +14.2%',
      'Revenue growth healthy at 11% YoY (Q3 FY25)',
    ],
    risks: [
      'RSI(14) near overbought zone at 71.3 — pullback possible',
    ],
  },
  {
    ticker: 'HDFCBANK',
    name: 'HDFC Bank Ltd.',
    price: '₹1,612.30',
    recommendation: 'hold',
    trend: 'side',
    trendLabel: '→ Sideways',
    horizon: 'Short Term · 3 Weeks',
    confidence: 61,
    reasons: [
      'Price consolidating between ₹1,580 and ₹1,650 support/resistance',
      'EMA 9 and EMA 21 converging — trend resolution imminent',
      'Fundamentals solid: P/E 18x, strong NII growth',
    ],
    risks: [
      'Breakout direction unclear — wait for confirmation above ₹1,655',
      'Broader market weakness could trigger range breakdown',
    ],
  },
  {
    ticker: 'ZOMATO',
    name: 'Zomato Ltd.',
    price: '₹208.45',
    recommendation: 'buy',
    trend: 'up',
    trendLabel: '↑ Uptrend',
    horizon: 'Short Term · 4 Weeks',
    confidence: 74,
    reasons: [
      '52-week breakout confirmed on above-average volume',
      'Momentum indicator (3M return: +38.7%) strongly bullish',
      'Quick Commerce segment driving re-rating from analysts',
      'EMA 9 crossed above EMA 21 last week — golden cross',
    ],
    risks: [
      'High P/E (120x) leaves limited margin of safety',
      'Profit booking likely near ₹225–230 resistance zone',
    ],
  },
  {
    ticker: 'TATASTEEL',
    name: 'Tata Steel Ltd.',
    price: '₹142.80',
    recommendation: 'sell',
    trend: 'down',
    trendLabel: '↓ Downtrend',
    horizon: 'Short Term · 3 Weeks',
    confidence: 68,
    reasons: [
      'Price below 200 DMA for 3 consecutive weeks',
      'Volume on down days 1.8× higher than up days — distribution pattern',
      'European operations reporting losses; guidance cut in Q3',
    ],
    risks: [
      'Any China steel demand pickup could reverse this call quickly',
      'Partial hedge: core India ops remain profitable',
    ],
  },
  {
    ticker: 'INFY',
    name: 'Infosys Ltd.',
    price: '₹1,478.55',
    recommendation: 'buy',
    trend: 'up',
    trendLabel: '↑ Uptrend',
    horizon: 'Long Term · 9 Months',
    confidence: 79,
    reasons: [
      'AI and cloud deal wins accelerating — deal TCV up 22% QoQ',
      'Price above all key EMAs (9, 21, 50, 200)',
      'Dividend yield 3.1% provides income cushion',
      '12M return momentum positive at +19.4%',
    ],
    risks: [
      'USD appreciation risk — revenue is USD-denominated',
      'Macro slowdown in US/Europe could delay IT spend recovery',
    ],
  },
  {
    ticker: 'IRFC',
    name: 'Indian Railway Finance Corp.',
    price: '₹175.20',
    recommendation: 'hold',
    trend: 'side',
    trendLabel: '→ Sideways',
    horizon: 'Medium Term · 6 Weeks',
    confidence: 55,
    reasons: [
      'Post-IPO run-up already priced in; valuation stretched vs peers',
      'Railway capex cycle intact — long-term thesis valid',
      'Dividend yield 1.1% provides some support',
    ],
    risks: [
      'Government policy changes could affect loan disbursement pipeline',
      'PSU sector rotation risk if broader market favors private banks',
    ],
  },
];

/**
 * Build the AI Picks tab in the DOM.
 * Called once on DOMContentLoaded — data is static for now.
 * To integrate backend: replace AI_PICKS_DATA with fetched JSON.
 */
function buildAIPicksTab() {
  const grid = document.getElementById('aiPicksGrid');
  if (!grid) return;

  grid.innerHTML = AI_PICKS_DATA.map(pick => buildAIPickCard(pick)).join('');

  // Animate confidence bars after paint
  requestAnimationFrame(() => {
    grid.querySelectorAll('.ai-conf-fill').forEach(el => {
      el.style.width = el.dataset.confidence + '%';
    });
  });
}

function buildAIPickCard(pick) {
  const trendCls = { up: 'trend-up', down: 'trend-down', side: 'trend-side' }[pick.trend] || 'trend-side';
  const recLabel = pick.recommendation.toUpperCase();

  const reasons = pick.reasons.map(r => `<li>${r}</li>`).join('');
  const risks   = pick.risks.map(r => `<div class="ai-risk-item">${r}</div>`).join('');

  return `
  <div class="ai-pick-card ${pick.recommendation}">
    <div class="ai-pick-header">
      <div class="ai-rec-badge ${pick.recommendation}">${recLabel}</div>
      <div class="ai-pick-meta">
        <div class="ai-pick-ticker">
          <a href="https://in.tradingview.com/chart/?symbol=NSE:${pick.ticker}" target="_blank" rel="noopener" style="color:#fff;">${pick.ticker}</a>
        </div>
        <div class="ai-pick-name">${pick.name}</div>
      </div>
      <div class="ai-pick-price" style="color:${pick.recommendation === 'buy' ? 'var(--green)' : pick.recommendation === 'sell' ? 'var(--red)' : 'var(--amber)'}">${pick.price}</div>
    </div>

    <div class="ai-pick-row">
      <span class="ai-trend-chip ${trendCls}">${pick.trendLabel}</span>
      <span class="ai-horizon-chip">⏱ ${pick.horizon}</span>
    </div>

    <div class="ai-conf-wrap">
      <div class="ai-conf-label">
        <span>AI Confidence</span>
        <strong>${pick.confidence}%</strong>
      </div>
      <div class="ai-conf-track">
        <div class="ai-conf-fill ${pick.recommendation}" data-confidence="${pick.confidence}" style="width:0%"></div>
      </div>
    </div>

    <hr class="ai-pick-divider">

    <div class="ai-pick-section-title">Why</div>
    <ul class="ai-pick-reasons">${reasons}</ul>

    <hr class="ai-pick-divider">

    <div class="ai-pick-section-title">Risk Indicators</div>
    ${risks}

    <div class="ai-pick-footer">
      <a class="ai-chart-link" href="https://in.tradingview.com/chart/?symbol=NSE:${pick.ticker}" target="_blank" rel="noopener">📊 Chart ↗</a>
      <span class="ai-pick-demo-tag">Demo Data</span>
    </div>
  </div>`;
}
