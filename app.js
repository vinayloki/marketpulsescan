/**
 * MarketPulse India — Main App
 * 5 tabs: Opportunities (engine), Top Movers, Full Scan, News, About
 * Auto-loads on page open. Zero maintenance. GitHub Pages hosted.
 */

/* ═══════════════════════════════════════════════════════════════
   GLOBALS
═══════════════════════════════════════════════════════════════ */
let summaryData    = null;   // latest_scan_summary.json
let fullScanData   = [];     // full_summary.json -> stocks[]
let fundamentals   = {};     // fundamentals.json -> keyed by symbol
let newsData       = [];     // daily_news.json
let opportunitiesData = [];  // opportunities.json -> opportunities[]
let aiPicksData    = null;   // ai_picks.json -> full AI recommendations
let backtestData   = null;   // performance_report.json -> backtest stats
let regimeData     = null;   // market_regime.json -> current regime
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
    const [summRes, fullRes, fundRes, newsRes, oppRes, aiRes, btRes, regRes] = await Promise.allSettled([
      fetch('scan_results/latest_scan_summary.json'),
      fetch('scan_results/full_summary.json'),
      fetch('scan_results/fundamentals.json'),
      fetch('scan_results/daily_news.json'),
      fetch('scan_results/opportunities.json'),
      fetch('scan_results/ai_picks.json'),
      fetch('scan_results/performance_report.json'),
      fetch('scan_results/market_regime.json'),
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

    // Parse AI picks
    if (aiRes && aiRes.status === 'fulfilled' && aiRes.value.ok) {
      aiPicksData = await aiRes.value.json();
      console.log(`✅ AI picks loaded: ${aiPicksData.total_stocks} stocks`);
    } else {
      console.warn('ai_picks.json not found — AI tab will show demo data');
    }




    // Parse backtest performance report

    if (btRes && btRes.status === 'fulfilled' && btRes.value.ok) {

      backtestData = await btRes.value.json();

      console.log('Backtest report loaded');

    }



    // Parse market regime

    if (regRes && regRes.status === 'fulfilled' && regRes.value.ok) {

      regimeData = await regRes.value.json();

      console.log('Market regime: ' + regimeData.regime);

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

  // Live regime badge in header (requires regimeBadge element in HTML)
  const regBadge = document.getElementById('regimeBadge');
  if (regBadge && regimeData) {
    const r   = regimeData.regime || 'Bull';
    const pctVal = regimeData.pct_vs_ema200;
    const pctStr = pctVal != null ? ' ' + (pctVal > 0 ? '+' : '') + pctVal + '%' : '';
    const cls = r === 'Bull' ? 'regime-bull' : r === 'Bear' ? 'regime-bear' : 'regime-side';
    regBadge.innerHTML = '<span class="regime-pill ' + cls + '">' + (r === 'Bull' ? '\u25b2' : r === 'Bear' ? '\u25bc' : '\u2192') + ' ' + r + pctStr + '</span>';
  }

  buildStatsRow();
  buildOpportunities();
  buildTopMovers();
  buildFullScan();
  buildNews();
  buildAIPicksTab();
  buildBacktestTab();
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
   AI PICKS TAB — Live Data Renderer (real ai_picks.json)
   Falls back to demo cards if ai_picks.json not yet generated.
═══════════════════════════════════════════════════════════════ */

// Filter + pagination state for AI picks table
let _aiRec = '', _aiSearch = '', _aiSector = '', _aiCap = '', _aiPage = 0;
const AI_PAGE = 50;

const AI_DEMO_PICKS = [
  { ticker:'RELIANCE', name:'Reliance Industries Ltd.', price:'2847.60', recommendation:'buy', trend:'up', trend_label:'↑ Uptrend', sector:'Energy', cap_label:'Large Cap', horizon:'Medium Term · 2 Months', confidence:82,
    tf_details:{'1W':{pct:2.1},'2W':{pct:4.3},'1M':{pct:9.2},'3M':{pct:14.2},'6M':{pct:18.1},'12M':{pct:22.4}},
    reasons:['Uptrend confirmed across 6 timeframes','Strong 3-month momentum: +14.2%','Solid long-term trend: +22.4% (12M)'],
    risks:['RSI near overbought — short-term pullback possible'] },
  { ticker:'HDFCBANK', name:'HDFC Bank Ltd.', price:'1612.30', recommendation:'hold', trend:'sideways', trend_label:'→ Sideways', sector:'Financial Services', cap_label:'Large Cap', horizon:'Short Term · 3 Weeks', confidence:61,
    tf_details:{'1W':{pct:0.5},'2W':{pct:-1.2},'1M':{pct:1.8},'3M':{pct:3.1},'6M':{pct:5.0},'12M':{pct:8.4}},
    reasons:['Price consolidating — no clear directional trend yet','Fundamentals solid: strong NII growth'],
    risks:['Awaiting breakout direction confirmation'] },
  { ticker:'ZOMATO', name:'Zomato Ltd.', price:'208.45', recommendation:'buy', trend:'up', trend_label:'↑ Uptrend', sector:'Consumer Services', cap_label:'Large Cap', horizon:'Short Term · 4 Weeks', confidence:74,
    tf_details:{'1W':{pct:8.1},'2W':{pct:15.3},'1M':{pct:22.7},'3M':{pct:38.7},'6M':{pct:45.0},'12M':{pct:62.1}},
    reasons:['52W breakout confirmed on volume','3M momentum: +38.7%','Quick Commerce re-rating underway'],
    risks:['High P/E — limited margin of safety'] },
  { ticker:'TATASTEEL', name:'Tata Steel Ltd.', price:'142.80', recommendation:'sell', trend:'down', trend_label:'↓ Downtrend', sector:'Metals', cap_label:'Large Cap', horizon:'Short Term · 3 Weeks', confidence:68,
    tf_details:{'1W':{pct:-3.2},'2W':{pct:-6.1},'1M':{pct:-9.3},'3M':{pct:-14.8},'6M':{pct:-11.2},'12M':{pct:-18.0}},
    reasons:['Downtrend confirmed across timeframes','Volume distribution pressure'],
    risks:['China demand recovery could reverse call quickly'] },
];

function buildAIPicksTab() {
  const grid = document.getElementById('aiPicksGrid');
  if (!grid) return;
  if (aiPicksData) {
    buildAIPicksLive();
  } else {
    grid.innerHTML = AI_DEMO_PICKS.map(p => buildAIPickCard(p, true)).join('');
    animateConfBars(grid);
  }
}

// ── LIVE TABLE ─────────────────────────────────────────────────────────
function buildAIPicksLive() {
  const wrap = document.getElementById('aiPicksGrid');
  if (!wrap) return;
  const parentEl = wrap.closest('#tab-aipicks');
  if (!parentEl) return;

  if (!parentEl.querySelector('#aiLiveTable')) {
    const s = aiPicksData.summary;
    wrap.style.display = 'none';
    wrap.insertAdjacentHTML('afterend', `
      <div id="aiLiveTable">
        <div class="ai-live-summary">
          <div class="ai-live-stat" style="color:var(--green)"><span class="ai-live-stat-val">${s.buy}</span><span class="ai-live-stat-lbl">🟢 BUY</span></div>
          <div class="ai-live-stat" style="color:var(--amber)"><span class="ai-live-stat-val">${s.hold}</span><span class="ai-live-stat-lbl">🟡 HOLD</span></div>
          <div class="ai-live-stat" style="color:var(--red)"><span class="ai-live-stat-val">${s.sell}</span><span class="ai-live-stat-lbl">🔴 SELL</span></div>
          <div class="ai-live-stat" style="color:var(--blue)"><span class="ai-live-stat-val">${aiPicksData.total_stocks}</span><span class="ai-live-stat-lbl">Stocks</span></div>
          <div class="ai-live-stat" style="color:var(--primary)"><span class="ai-live-stat-val">${s.avg_confidence}%</span><span class="ai-live-stat-lbl">Avg Confidence</span></div>
        </div>
        <div class="ai-filter-bar">
          <input class="ai-filter-input" id="aiSearchInput" type="text" placeholder="🔍 Search ticker or name..." oninput="onAiSearch()">
          <div class="opp-chips" id="aiRecChips">
            <button class="chip active" id="aiChipAll"  onclick="onAiRec('')">ALL</button>
            <button class="chip"        id="aiChipBuy"  onclick="onAiRec('buy')">🟢 BUY ${s.buy}</button>
            <button class="chip"        id="aiChipHold" onclick="onAiRec('hold')">🟡 HOLD ${s.hold}</button>
            <button class="chip"        id="aiChipSell" onclick="onAiRec('sell')">🔴 SELL ${s.sell}</button>
          </div>
          <select class="opp-select" id="aiSectorSel" onchange="onAiSector()"><option value="">All Sectors</option></select>
          <select class="opp-select" id="aiCapSel" onchange="onAiCap()">
            <option value="">All Cap Sizes</option>
            <option value="L">Large Cap</option>
            <option value="M">Mid Cap</option>
            <option value="S">Small Cap</option>
          </select>
          <span class="opp-count" id="aiPickCount"></span>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th style="text-align:left">Ticker</th>
              <th style="text-align:left">Sector / Name</th>
              <th>Rec</th>
              <th>Conf</th>
              <th>Trend</th>
              <th>Entry</th>
              <th style="color:var(--red)">SL</th>
              <th style="color:var(--green)">TP</th>
              <th>R:R</th>
              <th>P(Win)</th>
              <th>Regime</th>
              <th>1W</th><th>2W</th><th>1M</th><th>3M</th><th>6M</th><th>12M</th>
              <th>Horizon</th>
            </tr></thead>
            <tbody id="aiPicksTbody"></tbody>
          </table>
        </div>
        <div class="pagination" id="aiPicksPag"></div>
      </div>`);

    const sectors = [...new Set(aiPicksData.picks.map(p => p.sector).filter(Boolean))].sort();
    const secSel = document.getElementById('aiSectorSel');
    sectors.forEach(s => { const o = document.createElement('option'); o.value = s; o.textContent = s; secSel.appendChild(o); });
  }

  renderAIPicksTable();
}

function renderAIPicksTable() {
  if (!aiPicksData) return;
  let data = aiPicksData.picks;

  if (_aiRec)    data = data.filter(p => p.recommendation === _aiRec);
  if (_aiSearch) data = data.filter(p => p.ticker.includes(_aiSearch) || (p.name||'').toUpperCase().includes(_aiSearch));
  if (_aiSector) data = data.filter(p => p.sector === _aiSector);
  if (_aiCap)    data = data.filter(p => p.mcap_code === _aiCap);

  const total = data.length;
  const page  = data.slice(_aiPage * AI_PAGE, (_aiPage + 1) * AI_PAGE);

  const countEl = document.getElementById('aiPickCount');
  if (countEl) countEl.textContent = `${total.toLocaleString()} stocks`;

  const pct = v => v == null
    ? '<td class="na">—</td>'
    : `<td class="${v >= 8 ? 'pos bold-md' : v >= 2 ? 'pos' : v <= -8 ? 'neg bold-md' : v <= -2 ? 'neg' : ''}">${v >= 0 ? '▲' : '▼'} ${Math.abs(v).toFixed(1)}%</td>`;

  const trendCls = { up:'trend-up', down:'trend-down', sideways:'trend-side' };
  const recColor = { buy:'var(--green)', hold:'var(--amber)', sell:'var(--red)' };

  const tbodyEl = document.getElementById('aiPicksTbody');
  if (!tbodyEl) return;
  tbodyEl.innerHTML = page.map(p => {
    const td = p.tf_details || {};
    const displayName = (p.name && p.name !== p.ticker) ? p.name : '';
    const pSuccessColor = p.p_success >= 60 ? 'var(--green)' : p.p_success >= 45 ? 'var(--amber)' : 'var(--red)';
    const rrColor = (p.risk_reward||0) >= 1.5 ? 'var(--emerald)' : 'var(--amber)';
    const regimeCls = p.regime === 'Bull' ? 'regime-bull' : p.regime === 'Bear' ? 'regime-bear' : 'regime-side';
    return `<tr>
      <td class="td-ticker"><a href="https://in.tradingview.com/chart/?symbol=NSE:${p.ticker}" target="_blank" rel="noopener">${p.ticker}</a></td>
      <td style="text-align:left;max-width:160px">
        <div style="font-size:11px;color:rgba(255,255,255,0.5);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${displayName}</div>
        <div style="font-size:10px;color:rgba(255,255,255,0.25)">${p.sector||p.cap_label}</div>
      </td>
      <td style="text-align:center"><span class="ai-rec-badge ${p.recommendation}" style="font-size:10px;padding:2px 8px">${p.recommendation.toUpperCase()}</span></td>
      <td style="font-family:var(--mono);text-align:center;color:${recColor[p.recommendation]}">${p.confidence}%</td>
      <td style="text-align:center"><span class="ai-trend-chip ${trendCls[p.trend]||'trend-side'}" style="font-size:9px;padding:2px 7px">${p.trend_label}</span></td>
      <td style="font-family:var(--mono);text-align:right;font-size:11px">₹${p.entry_price||p.price||'—'}</td>
      <td style="font-family:var(--mono);text-align:right;font-size:11px;color:var(--red)">₹${p.stop_loss||'—'}</td>
      <td style="font-family:var(--mono);text-align:right;font-size:11px;color:var(--green)">₹${p.take_profit||'—'}</td>
      <td style="font-family:var(--mono);text-align:center;font-size:11px;color:${rrColor}">${p.risk_reward||'—'}x</td>
      <td style="font-family:var(--mono);text-align:center;font-size:11px;color:${pSuccessColor}">${p.p_success||'—'}%</td>
      <td style="text-align:center"><span class="regime-pill-sm ${regimeCls}">${p.regime||'—'}</span></td>
      ${pct(td['1W']?.pct)}${pct(td['2W']?.pct)}${pct(td['1M']?.pct)}${pct(td['3M']?.pct)}${pct(td['6M']?.pct)}${pct(td['12M']?.pct)}
      <td style="font-size:10px;color:rgba(255,255,255,0.3);white-space:nowrap">${p.horizon}</td>
    </tr>`;
  }).join('');

  // Pagination
  const totalPages = Math.ceil(total / AI_PAGE);
  const pag = document.getElementById('aiPicksPag');
  if (!pag) return;
  if (totalPages <= 1) { pag.innerHTML = ''; return; }
  const pages = [];
  pages.push(`<button class="pg-btn" onclick="aiGo(Math.max(0,${_aiPage}-1))">← Prev</button>`);
  const s = Math.max(0, _aiPage - 2), e = Math.min(totalPages, _aiPage + 5);
  if (s > 0) pages.push(`<button class="pg-btn" onclick="aiGo(0)">1</button><span style="color:rgba(255,255,255,0.2)">…</span>`);
  for (let i = s; i < e; i++) pages.push(`<button class="pg-btn ${i === _aiPage ? 'active' : ''}" onclick="aiGo(${i})">${i+1}</button>`);
  if (e < totalPages) pages.push(`<span style="color:rgba(255,255,255,0.2)">…</span><button class="pg-btn" onclick="aiGo(${totalPages-1})">${totalPages}</button>`);
  pages.push(`<button class="pg-btn" onclick="aiGo(Math.min(${totalPages-1},${_aiPage}+1))">Next →</button>`);
  pag.innerHTML = pages.join('');
}

function aiGo(p)     { _aiPage = p; renderAIPicksTable(); window.scrollTo({top:400,behavior:'smooth'}); }
function onAiSearch(){ _aiSearch = document.getElementById('aiSearchInput').value.toUpperCase().trim(); _aiPage=0; renderAIPicksTable(); }
function onAiSector(){ _aiSector = document.getElementById('aiSectorSel').value; _aiPage=0; renderAIPicksTable(); }
function onAiCap()   { _aiCap = document.getElementById('aiCapSel').value; _aiPage=0; renderAIPicksTable(); }
function onAiRec(r)  {
  _aiRec = r; _aiPage = 0;
  ['aiChipAll','aiChipBuy','aiChipHold','aiChipSell'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove('active');
  });
  const idMap = {'':'aiChipAll','buy':'aiChipBuy','hold':'aiChipHold','sell':'aiChipSell'};
  const t = document.getElementById(idMap[r]);
  if (t) t.classList.add('active');
  renderAIPicksTable();
}

// ── CARD BUILDER (demo + can be reused for future card view) ───────────
function buildAIPickCard(pick, isDemo = false) {
  const trendCls = { up:'trend-up', down:'trend-down', sideways:'trend-side', side:'trend-side' }[pick.trend] || 'trend-side';
  const rec = pick.recommendation;
  const recColor = rec === 'buy' ? 'var(--green)' : rec === 'sell' ? 'var(--red)' : 'var(--amber)';
  const reasons = (pick.reasons||[]).map(r => `<li>${r}</li>`).join('');
  const risks   = (pick.risks||[]).map(r => `<div class="ai-risk-item">${r}</div>`).join('');
  const tfd = pick.tf_details || {};
  const tfRow = ['1W','2W','1M','3M','6M','12M'].map(tf => {
    const d = tfd[tf];
    if (!d || d.pct == null) return `<div class="mc-tf-cell na">—</div>`;
    return `<div class="mc-tf-cell ${d.pct >= 0 ? 'up' : 'dn'}">${d.pct >= 0 ? '+' : ''}${d.pct.toFixed(1)}%</div>`;
  }).join('');

  return `
  <div class="ai-pick-card ${rec}">
    <div class="ai-pick-header">
      <div class="ai-rec-badge ${rec}">${rec.toUpperCase()}</div>
      <div class="ai-pick-meta">
        <div class="ai-pick-ticker"><a href="https://in.tradingview.com/chart/?symbol=NSE:${pick.ticker}" target="_blank" rel="noopener" style="color:#fff">${pick.ticker}</a></div>
        <div class="ai-pick-name">${(pick.name && pick.name !== pick.ticker) ? pick.name : (pick.sector||pick.cap_label||'')}</div>
      </div>
      <div class="ai-pick-price" style="color:${recColor}">₹${pick.price}</div>
    </div>
    <div class="ai-pick-row">
      <span class="ai-trend-chip ${trendCls}">${pick.trend_label||pick.trendLabel||''}</span>
      <span class="ai-horizon-chip">⏱ ${pick.horizon}</span>
    </div>
    <div class="ai-conf-wrap">
      <div class="ai-conf-label"><span>AI Confidence</span><strong>${pick.confidence}%</strong></div>
      <div class="ai-conf-track">
        <div class="ai-conf-fill ${rec}" data-confidence="${pick.confidence}" style="width:0%"></div>
      </div>
    </div>
    <div class="mc-tf-header">${['1W','2W','1M','3M','6M','12M'].map(tf=>`<div class="mc-tf-h">${tf}</div>`).join('')}</div>
    <div class="mc-tfs" style="margin-bottom:10px">${tfRow}</div>
    <hr class="ai-pick-divider">
    <div class="ai-pick-section-title">Why</div>
    <ul class="ai-pick-reasons">${reasons}</ul>
    <hr class="ai-pick-divider">
    <div class="ai-pick-section-title">Risk Indicators</div>
    ${risks}
    <div class="ai-pick-footer">
      <a class="ai-chart-link" href="https://in.tradingview.com/chart/?symbol=NSE:${pick.ticker}" target="_blank" rel="noopener">📊 Chart ↗</a>
      ${isDemo ? '<span class="ai-pick-demo-tag">Demo</span>' : ''}
    </div>
  </div>`;
}

function animateConfBars(parentEl) {
  requestAnimationFrame(() => {
    (parentEl || document).querySelectorAll('.ai-conf-fill').forEach(el => {
      el.style.width = el.dataset.confidence + '%';
    });
  });
}

/* ═══════════════════════════════════════════════════════════════
   BACKTEST TAB
═══════════════════════════════════════════════════════════════ */
function buildBacktestTab() {
  const el = document.getElementById('tab-backtest');
  if (!el) return;

  if (!backtestData) {
    el.innerHTML = `<div style="padding:60px;text-align:center;color:rgba(255,255,255,0.3)">
      <div style="font-size:48px;margin-bottom:16px">🧪</div>
      <div style="font-size:18px;font-weight:600;margin-bottom:8px">No Backtest Data Yet</div>
      <div style="font-size:14px">Run <code style="background:rgba(255,255,255,0.08);padding:2px 8px;border-radius:4px">python backtest.py</code> then <code style="background:rgba(255,255,255,0.08);padding:2px 8px;border-radius:4px">python performance.py</code></div>
    </div>`;
    return;
  }

  const cfg = backtestData.config || {};
  const cmp = backtestData.comparison || {};
  const mA  = backtestData.mode_a || {};
  const mB  = backtestData.mode_b || {};

  const fmt   = n  => n != null ? n.toLocaleString() : '—';
  const pct   = n  => n != null ? `${n > 0 ? '+' : ''}${n.toFixed(2)}%` : '—';
  const money = n  => n != null ? `₹${Math.round(n).toLocaleString()}` : '—';

  const statCard = (val, lbl, color='') => `
    <div class="bt-stat-card">
      <div class="bt-stat-val" style="color:${color||'var(--blue)'}">${val}</div>
      <div class="bt-stat-lbl">${lbl}</div>
    </div>`;

  const viableIcon = s => s?.can_achieve_3_5pct_goal ? '✅' : s?.expectancy_pct > 0 ? '⚠️' : '❌';

  const regimeTable = s => {
    if (!s?.regime_breakdown) return '';
    const rows = Object.entries(s.regime_breakdown).map(([r, d]) => {
      const cls = r === 'Bull' ? 'var(--green)' : r === 'Bear' ? 'var(--red)' : 'var(--amber)';
      return `<tr>
        <td><span style="color:${cls};font-weight:600">${r}</span></td>
        <td style="text-align:right">${d.trades}</td>
        <td style="text-align:right">${d.win_rate_pct}%</td>
        <td style="text-align:right;color:${d.avg_return>=0?'var(--green)':'var(--red)'}">${d.avg_return>=0?'+':''}${d.avg_return}%</td>
        <td style="text-align:right;color:${d.expectancy>=0?'var(--green)':'var(--red)'}">${d.expectancy>=0?'+':''}${d.expectancy}%</td>
      </tr>`;
    }).join('');
    return `<table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead><tr style="color:rgba(255,255,255,0.4);font-size:11px">
        <th style="text-align:left">Regime</th>
        <th style="text-align:right">Trades</th>
        <th style="text-align:right">Win Rate</th>
        <th style="text-align:right">Avg Return</th>
        <th style="text-align:right">Expectancy</th>
      </tr></thead><tbody>${rows}</tbody></table>`;
  };

  const signalTable = s => {
    if (!s?.signal_breakdown) return '';
    const rows = Object.entries(s.signal_breakdown).map(([sig, d]) => {
      return `<tr>
        <td style="font-weight:600">${sig}</td>
        <td style="text-align:right">${d.trades}</td>
        <td style="text-align:right">${d.win_rate_pct}%</td>
        <td style="text-align:right;color:${d.avg_return>=0?'var(--green)':'var(--red)'}">${d.avg_return>=0?'+':''}${d.avg_return}%</td>
      </tr>`;
    }).join('');
    return `<table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead><tr style="color:rgba(255,255,255,0.4);font-size:11px">
        <th style="text-align:left">Signal</th>
        <th style="text-align:right">Trades</th>
        <th style="text-align:right">Win Rate</th>
        <th style="text-align:right">Avg Return</th>
      </tr></thead><tbody>${rows}</tbody></table>`;
  };

  const equityCurveChart = (curve, modeLabel) => {
    if (!curve || !curve.length) return '';
    const max = Math.max(...curve.map(p => p.equity));
    const min = Math.min(...curve.map(p => p.equity));
    const range = max - min || 1;
    const w = 400, h = 80;
    const pts = curve.map((p, i) => {
      const x = (i / (curve.length - 1)) * w;
      const y = h - ((p.equity - min) / range) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    return `
      <div style="margin-top:12px">
        <div style="font-size:11px;color:rgba(255,255,255,0.4);margin-bottom:4px">${modeLabel} — Equity Curve (last ${curve.length} trades)</div>
        <svg viewBox="0 0 ${w} ${h}" style="width:100%;height:80px;background:rgba(255,255,255,0.03);border-radius:6px">
          <polyline points="${pts}" fill="none" stroke="var(--emerald)" stroke-width="1.5"/>
        </svg>
      </div>`;
  };

  const modePanel = (s, mode, label) => {
    if (!s || !s.total_trades) return `<div style="padding:20px;color:rgba(255,255,255,0.3);text-align:center">No ${label} trades</div>`;
    const verdict_color = s.can_achieve_3_5pct_goal ? 'var(--green)' : s.expectancy_pct > 0 ? 'var(--amber)' : 'var(--red)';
    return `
      <div class="bt-panel">
        <div class="bt-panel-title">${label}</div>
        <div class="bt-stats-grid">
          ${statCard(s.total_trades||0, 'Total Trades', 'var(--blue)')}
          ${statCard((s.win_rate_pct||0)+'%', 'Win Rate', s.win_rate_pct>=50?'var(--green)':'var(--red)')}
          ${statCard(pct(s.expectancy_pct), 'Expectancy', s.expectancy_pct>=0?'var(--green)':'var(--red)')}
          ${statCard((s.profit_factor||0)+'x', 'Profit Factor', s.profit_factor>=1.2?'var(--emerald)':'var(--amber)')}
          ${statCard((s.max_drawdown_pct||0)+'%', 'Max Drawdown', 'var(--red)')}
          ${statCard((s.sharpe_like||0), 'Sharpe-like', s.sharpe_like>=0.5?'var(--green)':'var(--amber)')}
          ${statCard(money(s.total_pnl), 'Total P&L', s.total_pnl>=0?'var(--green)':'var(--red)')}
          ${statCard(money(s.final_capital), 'Final Capital', 'var(--primary)')}
          ${statCard(pct(s.total_return_pct), 'Total Return', s.total_return_pct>=0?'var(--green)':'var(--red)')}
          ${statCard((s.target_hit_rate_pct||0)+'%', '3-5% Target Rate', 'var(--emerald)')}
        </div>
        <div class="bt-verdict" style="color:${verdict_color}">
          ${viableIcon(s)} ${s.viability_verdict||s.verdict||'—'}
        </div>
        ${equityCurveChart(s.equity_curve, label)}
        <div style="margin-top:20px">
          <div class="bt-section-title">Regime Breakdown</div>
          ${regimeTable(s)}
        </div>
        <div style="margin-top:16px">
          <div class="bt-section-title">Signal Breakdown</div>
          ${signalTable(s)}
        </div>
      </div>`;
  };

  el.innerHTML = `
    <div class="bt-container">
      <div class="bt-header">
        <div>
          <div style="font-size:20px;font-weight:700;margin-bottom:4px">Backtest Results</div>
          <div style="font-size:12px;color:rgba(255,255,255,0.4)">
            ${backtestData.generated||''}  &middot;
            TP=${cfg.take_profit_pct||4}%  SL&ge;${cfg.stop_loss_fixed_pct||2}% (ATR${cfg.atr_period||14}&times;${cfg.atr_sl_multiplier||1.5})
            &middot;  Hold&le;${cfg.max_hold_days||5}d  &middot;  Window: ${cfg.backtest_weeks||52}wk
          </div>
        </div>
        <div style="text-align:right;font-size:12px;color:rgba(255,255,255,0.4)">
          Capital: ₹${(cfg.capital||1000000).toLocaleString()}<br>
          Risk/trade: ${cfg.risk_per_trade_pct||1.5}%
        </div>
      </div>

      <div class="bt-ai-edge">
        <div class="bt-edge-item">
          <div class="bt-edge-lbl">Mode A Expectancy</div>
          <div class="bt-edge-val" style="color:${(cmp.mode_a_expectancy||0)>=0?'var(--green)':'var(--red)'}">${pct(cmp.mode_a_expectancy)}</div>
        </div>
        <div class="bt-edge-arrow">→</div>
        <div class="bt-edge-item">
          <div class="bt-edge-lbl">Mode B Expectancy</div>
          <div class="bt-edge-val" style="color:${(cmp.mode_b_expectancy||0)>=0?'var(--green)':'var(--red)'}">${pct(cmp.mode_b_expectancy)}</div>
        </div>
        <div style="border-left:1px solid rgba(255,255,255,0.1);padding-left:24px;margin-left:12px">
          <div class="bt-edge-lbl">AI Filtering Edge</div>
          <div class="bt-edge-val" style="color:${(cmp.ai_filtering_edge||0)>0?'var(--emerald)':'var(--amber)'}">
            ${(cmp.ai_filtering_edge||0)>0?'+':''}${(cmp.ai_filtering_edge||0).toFixed(2)}%
          </div>
          <div style="font-size:10px;color:rgba(255,255,255,0.3);margin-top:2px">${cmp.recommendation||''}</div>
        </div>
      </div>

      <div class="bt-modes">
        ${modePanel(mA, 'A', 'Mode A — Full NSE Universe')}
        ${modePanel(mB, 'B', 'Mode B — AI-Filtered Picks')}
      </div>
    </div>

    <style>
      .bt-container{padding:24px;max-width:1400px;margin:0 auto}
      .bt-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid rgba(255,255,255,0.08)}
      .bt-stats-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px;margin-bottom:16px}
      .bt-stat-card{background:rgba(255,255,255,0.05);border-radius:8px;padding:12px;text-align:center}
      .bt-stat-val{font-size:18px;font-weight:700;font-family:var(--mono);margin-bottom:4px}
      .bt-stat-lbl{font-size:10px;color:rgba(255,255,255,0.4)}
      .bt-panel{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:20px;margin-bottom:20px}
      .bt-panel-title{font-size:14px;font-weight:700;margin-bottom:16px;color:rgba(255,255,255,0.9)}
      .bt-verdict{font-size:13px;font-weight:600;margin:16px 0;padding:10px 14px;background:rgba(0,0,0,0.2);border-radius:6px}
      .bt-section-title{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,0.4);margin-bottom:8px}
      .bt-modes{display:grid;grid-template-columns:1fr 1fr;gap:20px}
      @media(max-width:900px){.bt-modes{grid-template-columns:1fr}}
      .bt-ai-edge{display:flex;align-items:center;gap:20px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:16px 20px;margin-bottom:20px}
      .bt-edge-item{text-align:center}
      .bt-edge-lbl{font-size:10px;color:rgba(255,255,255,0.4);margin-bottom:4px}
      .bt-edge-val{font-size:22px;font-weight:700;font-family:var(--mono)}
      .bt-edge-arrow{font-size:24px;color:rgba(255,255,255,0.2)}
      .regime-pill{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600}
      .regime-pill.regime-bull{background:rgba(34,197,94,0.15);color:#22c55e;border:1px solid rgba(34,197,94,0.3)}
      .regime-pill.regime-bear{background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid rgba(239,68,68,0.3)}
      .regime-pill.regime-side{background:rgba(245,158,11,0.15);color:#f59e0b;border:1px solid rgba(245,158,11,0.3)}
      .regime-pill-sm{display:inline-block;padding:2px 7px;border-radius:10px;font-size:9px;font-weight:600}
      .regime-pill-sm.regime-bull{background:rgba(34,197,94,0.15);color:#22c55e}
      .regime-pill-sm.regime-bear{background:rgba(239,68,68,0.15);color:#ef4444}
      .regime-pill-sm.regime-side{background:rgba(245,158,11,0.15);color:#f59e0b}
    </style>`;
}
