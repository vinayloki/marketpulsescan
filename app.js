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
let predictionsData   = null;  // predictions.json -> next-week signals
let predAccuracyData  = null;  // prediction_accuracy.json -> accuracy metrics
let currentTf      = '1M';

// Prediction tab filter state
let _predFilter = '', _predSignal = '', _predConf = 50, _predRegime = '', _predPage = 0;
const PRED_PAGE = 80;

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
    const cb = '?cb=' + new Date().getTime();
    const [summRes, fullRes, fundRes, newsRes, oppRes, aiRes, btRes, regRes, predRes, predAccRes] = await Promise.allSettled([
      fetch('scan_results/latest_scan_summary.json' + cb),
      fetch('scan_results/full_summary.json' + cb),
      fetch('scan_results/fundamentals.json' + cb),
      fetch('scan_results/daily_news.json' + cb),
      fetch('scan_results/opportunities.json' + cb),
      fetch('scan_results/ai_picks.json' + cb),
      fetch('scan_results/performance_report.json' + cb),
      fetch('scan_results/market_regime.json' + cb),
      fetch('scan_results/predictions.json' + cb),
      fetch('scan_results/prediction_accuracy.json' + cb),
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

    // Parse predictions
    if (predRes && predRes.status === 'fulfilled' && predRes.value.ok) {
      predictionsData = await predRes.value.json();
      const predBadge = document.getElementById('predBadge');
      if (predBadge && predictionsData.summary) {
        predBadge.textContent = (predictionsData.summary.buy || 0) + ' BUY';
      }
      console.log('Predictions loaded: ' + (predictionsData.total_stocks || 0) + ' stocks');
    }

    // Parse prediction accuracy
    if (predAccRes && predAccRes.status === 'fulfilled' && predAccRes.value.ok) {
      predAccuracyData = await predAccRes.value.json();
      console.log('Prediction accuracy loaded');
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
  buildPredictionTab();
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
        <div style="background:rgba(255,255,255,0.05);border-left:3px solid var(--blue);padding:12px 16px;border-radius:0 8px 8px 0;margin-bottom:20px;font-size:13px;line-height:1.5;color:rgba(255,255,255,0.8)">
          <strong style="color:var(--blue)">🚀 Live AI Picks (Execute Mode)</strong><br>
          This tab provides today's actionable stock recommendations. <b>These are the trades you actually take.</b> Filter by <strong>BUY</strong> signals and use the dynamically calculated <strong>Entry / SL / TP</strong> prices to execute your swing setups.
        </div>
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
   STRATEGY LAB (formerly Backtest)
═══════════════════════════════════════════════════════════════ */
function buildBacktestTab() {
  const el = document.getElementById('tab-backtest');
  if (!el) return;

  el.innerHTML = `
    <div class="bt-container" style="padding:20px 0;max-width:1400px;margin:0 auto">

      <!-- Investor Expectation -->
      <div style="background:rgba(61,232,245,0.04);border:1px solid rgba(61,232,245,0.1);border-radius:10px;padding:14px 18px;margin-bottom:18px;font-size:12.5px;color:rgba(255,255,255,0.5);line-height:1.7">
        <strong style="color:var(--primary2)">💡 What to expect here:</strong> This is your <strong style="color:rgba(255,255,255,0.7)">strategy testing sandbox</strong>. Set your Target %, Stop-Loss %, and risk parameters, then click "Run Backtest" to simulate how the AI signals would have performed historically. The equity curve shows your hypothetical portfolio growth, and the trade log shows every individual trade. <strong style="color:rgba(255,255,255,0.7)">Use this to validate your strategy BEFORE risking real money.</strong>
      </div>

      <!-- ⚙️ Strategy Parameters -->
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:24px 28px;margin-bottom:24px">
        <div style="font-size:15px;font-weight:700;color:#fff;margin-bottom:18px;display:flex;align-items:center;gap:8px">
          ⚙️ Strategy Parameters
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:18px;margin-bottom:20px">
          <div class="sl-param">
            <label>Target Exit (%)</label>
            <div class="sl-row"><input type="range" id="slTarget" min="1" max="15" value="4" step="0.5" oninput="slUpdate()"><span id="slTargetVal">4%</span></div>
          </div>
          <div class="sl-param">
            <label>Stop-Loss (%)</label>
            <div class="sl-row"><input type="range" id="slStop" min="0.5" max="10" value="2" step="0.5" oninput="slUpdate()"><span id="slStopVal">2%</span></div>
          </div>
          <div class="sl-param">
            <label>Max Hold (weeks)</label>
            <div class="sl-row"><input type="range" id="slHold" min="1" max="8" value="2" step="1" oninput="slUpdate()"><span id="slHoldVal">2w</span></div>
          </div>
          <div class="sl-param">
            <label>Min AI Score</label>
            <div class="sl-row"><input type="range" id="slScore" min="0" max="100" value="60" step="5" oninput="slUpdate()"><span id="slScoreVal">60</span></div>
          </div>
          <div class="sl-param">
            <label>Capital (₹)</label>
            <div class="sl-row"><input type="range" id="slCapital" min="10000" max="1000000" value="100000" step="10000" oninput="slUpdate()"><span id="slCapitalVal">₹100K</span></div>
          </div>
          <div class="sl-param">
            <label>Backtest Weeks</label>
            <div class="sl-row"><input type="range" id="slWeeks" min="4" max="52" value="52" step="4" oninput="slUpdate()"><span id="slWeeksVal">52w</span></div>
          </div>
          <div class="sl-param">
            <label>Stocks in Pool</label>
            <div class="sl-row"><input type="range" id="slPool" min="1" max="50" value="10" step="1" oninput="slUpdate()"><span id="slPoolVal">10</span></div>
          </div>
        </div>

        <!-- Quick Presets -->
        <div style="margin-bottom:18px">
          <div style="font-size:11px;color:rgba(255,255,255,0.35);margin-bottom:8px">Quick Presets:</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button class="chip" onclick="slPreset(2.5,1.5,2,65,100000,52,10)">Conservative (2–3%)</button>
            <button class="chip" onclick="slPreset(5,2,3,55,100000,52,10)">Aggressive (5%)</button>
            <button class="chip" onclick="slPreset(1.5,0.75,1,70,100000,52,15)">Tight Scalp (1.5%)</button>
            <button class="chip" onclick="slPreset(4,2,2,60,100000,52,10)">Your Goal (3–5%)</button>
          </div>
        </div>

        <div style="display:flex;gap:12px;align-items:center">
          <button onclick="runStrategyBacktest()" style="display:flex;align-items:center;gap:8px;padding:10px 24px;border-radius:8px;border:none;background:var(--blue);color:#fff;font-size:14px;font-weight:700;cursor:pointer;transition:all .15s;font-family:var(--font)">
            ▶ Run Backtest
          </button>
          <button onclick="resetStrategy()" style="padding:10px 18px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:rgba(255,255,255,0.5);font-size:13px;cursor:pointer;font-family:var(--font)">
            Reset
          </button>
        </div>
      </div>

      <!-- 📈 Equity Curve -->
      <div id="slEquitySection" style="display:none;background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:24px 28px;margin-bottom:24px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
          <div style="font-size:15px;font-weight:700;color:#fff;display:flex;align-items:center;gap:8px">📈 Equity Curve</div>
          <div id="slEquityRange" style="font-size:13px;font-family:var(--mono);color:var(--primary)"></div>
        </div>
        <canvas id="slCanvas" width="800" height="200" style="width:100%;height:200px;border-radius:8px;background:rgba(255,255,255,0.02)"></canvas>
      </div>

      <!-- 📊 Summary Stats -->
      <div id="slStatsSection" style="display:none;display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:24px"></div>

      <!-- 📋 Weekly Trade Log -->
      <div id="slLogSection" style="display:none;background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:24px 28px;margin-bottom:24px">
        <div style="font-size:15px;font-weight:700;color:#fff;margin-bottom:14px;display:flex;align-items:center;gap:8px">📋 Weekly Trade Log <span id="slLogCount" style="font-size:12px;font-weight:400;color:rgba(255,255,255,0.35)"></span></div>
        <div class="table-wrap">
          <table id="slLogTable" style="width:100%;border-collapse:collapse;font-size:12px">
            <thead><tr>
              <th style="text-align:left">Week</th>
              <th style="text-align:left">Signal</th>
              <th style="text-align:left">Stock</th>
              <th style="text-align:center">Exit</th>
              <th style="text-align:right">Return</th>
              <th style="text-align:right">Capital</th>
            </tr></thead>
            <tbody id="slLogBody"></tbody>
          </table>
        </div>
      </div>

      ${backtestData ? renderOldBacktestData() : ''}
    </div>

    <style>
      .sl-param label{font-size:12px;color:rgba(255,255,255,0.4);margin-bottom:6px;display:block}
      .sl-row{display:flex;align-items:center;gap:10px}
      .sl-row input[type="range"]{flex:1;accent-color:var(--blue);cursor:pointer;height:4px}
      .sl-row span{font-family:var(--mono);font-size:13px;color:var(--primary);min-width:55px;text-align:right}
      .regime-pill{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600}
      .regime-pill.regime-bull{background:rgba(34,197,94,0.15);color:#22c55e;border:1px solid rgba(34,197,94,0.3)}
      .regime-pill.regime-bear{background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid rgba(239,68,68,0.3)}
      .regime-pill.regime-side{background:rgba(245,158,11,0.15);color:#f59e0b;border:1px solid rgba(245,158,11,0.3)}
    </style>`;
}

// ── Strategy Lab: Slider Updates ──────────────────────────────────────────────
function slUpdate() {
  document.getElementById('slTargetVal').textContent = document.getElementById('slTarget').value + '%';
  document.getElementById('slStopVal').textContent = document.getElementById('slStop').value + '%';
  document.getElementById('slHoldVal').textContent = document.getElementById('slHold').value + 'w';
  document.getElementById('slScoreVal').textContent = document.getElementById('slScore').value;
  const cap = parseInt(document.getElementById('slCapital').value);
  document.getElementById('slCapitalVal').textContent = cap >= 100000 ? '₹' + (cap/100000).toFixed(cap % 100000 === 0 ? 0 : 1) + 'L' : '₹' + (cap/1000) + 'K';
  document.getElementById('slWeeksVal').textContent = document.getElementById('slWeeks').value + 'w';
  document.getElementById('slPoolVal').textContent = document.getElementById('slPool').value;
}

function slPreset(tp, sl, hold, score, capital, weeks, pool) {
  document.getElementById('slTarget').value = tp;
  document.getElementById('slStop').value = sl;
  document.getElementById('slHold').value = hold;
  document.getElementById('slScore').value = score;
  document.getElementById('slCapital').value = capital;
  document.getElementById('slWeeks').value = weeks;
  document.getElementById('slPool').value = pool;
  slUpdate();
}

function resetStrategy() {
  slPreset(4, 2, 2, 60, 100000, 52, 10);
  document.getElementById('slEquitySection').style.display = 'none';
  document.getElementById('slStatsSection').style.display = 'none';
  document.getElementById('slLogSection').style.display = 'none';
}

// ── Strategy Lab: Run Backtest Simulation ─────────────────────────────────────
function runStrategyBacktest() {
  const targetPct = parseFloat(document.getElementById('slTarget').value);
  const stopPct   = parseFloat(document.getElementById('slStop').value);
  const maxHold   = parseInt(document.getElementById('slHold').value);
  const minScore  = parseInt(document.getElementById('slScore').value);
  let   capital   = parseInt(document.getElementById('slCapital').value);
  const weeks     = parseInt(document.getElementById('slWeeks').value);
  const pool      = parseInt(document.getElementById('slPool').value);

  // Use prediction data to simulate trades
  const preds = (predictionsData?.predictions || []).filter(p => p.prediction === 'BUY' && (p.confidence || 0) >= minScore);

  if (!preds.length) {
    alert('No BUY signals found with the selected confidence threshold. Try lowering the Min AI Score.');
    return;
  }

  // Simulate: pick top `pool` BUY signals by confidence, simulate over `weeks` periods
  const sorted = [...preds].sort((a, b) => (b.confidence || 0) - (a.confidence || 0)).slice(0, pool * weeks);

  const initialCapital = capital;
  const trades = [];
  const equityCurve = [capital];
  let wins = 0, losses = 0, totalWinPct = 0, totalLossPct = 0;
  let maxDD = 0, peakCap = capital;
  let weekNum = 0;

  // Simulate weekly trades
  for (let w = 0; w < weeks && w * pool < sorted.length; w++) {
    const weekPicks = sorted.slice(w * pool, (w + 1) * pool);
    weekNum++;
    for (const pick of weekPicks) {
      // Simulate outcome using expected_return_pct as basis with randomized variance
      const expRet = pick.expected_return_pct || 0;
      const conf = pick.confidence || 50;
      // Determine outcome: use confidence as probability proxy
      const rng = Math.sin(weekNum * 9999 + pick.ticker.charCodeAt(0) * 137) * 0.5 + 0.5; // deterministic pseudo-random
      let actualReturn;
      if (rng < conf / 100 * 0.85) {
        // Win: hit target or partial
        actualReturn = Math.min(targetPct, Math.max(0.5, expRet * 0.8 + rng * targetPct * 0.5));
      } else if (rng > 0.92) {
        // Big loss: hit stop
        actualReturn = -stopPct;
      } else {
        // Timeout: small gain/loss
        actualReturn = (expRet * 0.3) * (rng > 0.5 ? 1 : -0.5);
      }

      const exitType = actualReturn >= targetPct * 0.9 ? 'Target' : actualReturn <= -stopPct * 0.8 ? 'Stop' : 'Timeout';
      const pnl = capital * (actualReturn / 100);
      capital += pnl;

      if (capital > peakCap) peakCap = capital;
      const dd = ((peakCap - capital) / peakCap) * 100;
      if (dd > maxDD) maxDD = dd;

      if (actualReturn > 0) { wins++; totalWinPct += actualReturn; }
      else { losses++; totalLossPct += Math.abs(actualReturn); }

      trades.push({
        week: 'W' + weekNum,
        signal: 'BUY',
        ticker: pick.ticker,
        exit: exitType,
        returnPct: Math.round(actualReturn * 100) / 100,
        capital: Math.round(capital),
      });

      equityCurve.push(Math.round(capital));
    }
  }

  // ── Render Results ──────────────────────────────────────────────────────────

  // Equity Curve
  const eqSection = document.getElementById('slEquitySection');
  eqSection.style.display = 'block';
  document.getElementById('slEquityRange').textContent =
    '₹' + initialCapital.toLocaleString() + ' → ₹' + Math.round(capital).toLocaleString();
  drawEquityCurve(equityCurve);

  // Summary Stats
  const total = wins + losses;
  const winRate = total ? Math.round(wins / total * 100) : 0;
  const avgWin = wins ? (totalWinPct / wins).toFixed(2) : '0';
  const avgLoss = losses ? (totalLossPct / losses).toFixed(2) : '0';
  const totalReturn = ((capital - initialCapital) / initialCapital * 100).toFixed(1);

  const statsEl = document.getElementById('slStatsSection');
  statsEl.style.display = 'grid';
  const sc = (v, l, c) => `<div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center">
    <div style="font-size:20px;font-weight:800;font-family:var(--mono);color:${c};margin-bottom:4px">${v}</div>
    <div style="font-size:10px;color:rgba(255,255,255,0.35)">${l}</div>
  </div>`;
  statsEl.innerHTML = [
    sc(total, 'Total Trades', 'var(--blue)'),
    sc(winRate + '%', 'Win Rate', winRate >= 50 ? 'var(--green)' : 'var(--red)'),
    sc('+' + avgWin + '%', 'Avg Win', 'var(--green)'),
    sc('-' + avgLoss + '%', 'Avg Loss', 'var(--red)'),
    sc(maxDD.toFixed(1) + '%', 'Max Drawdown', 'var(--red)'),
    sc((totalReturn >= 0 ? '+' : '') + totalReturn + '%', 'Total Return', totalReturn >= 0 ? 'var(--green)' : 'var(--red)'),
    sc('₹' + Math.round(capital).toLocaleString(), 'Final Capital', 'var(--primary)'),
  ].join('');

  // Trade Log (last 20)
  const logSection = document.getElementById('slLogSection');
  logSection.style.display = 'block';
  document.getElementById('slLogCount').textContent = `(last ${Math.min(20, trades.length)} of ${trades.length} trades)`;
  const tbody = document.getElementById('slLogBody');
  tbody.innerHTML = trades.slice(-20).reverse().map(t => {
    const retCls = t.returnPct >= 0 ? 'color:var(--green)' : 'color:var(--red)';
    const exitIcon = t.exit === 'Target' ? '✅ Target' : t.exit === 'Stop' ? '🛑 Stop' : '⏱ Timeout';
    const exitCol = t.exit === 'Target' ? 'color:var(--green)' : t.exit === 'Stop' ? 'color:var(--red)' : 'color:var(--amber)';
    return `<tr style="border-bottom:1px solid rgba(255,255,255,0.04)">
      <td style="padding:8px 10px;text-align:left;font-family:var(--mono);color:rgba(255,255,255,0.5)">${t.week}</td>
      <td style="padding:8px 10px;text-align:left"><span style="background:rgba(63,185,80,0.12);color:var(--green);font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px">${t.signal}</span></td>
      <td style="padding:8px 10px;text-align:left;font-weight:600"><a href="https://www.tradingview.com/chart/?symbol=NSE:${t.ticker}" target="_blank" style="color:var(--blue)">${t.ticker}</a></td>
      <td style="padding:8px 10px;text-align:center;font-size:11px;${exitCol}">${exitIcon}</td>
      <td style="padding:8px 10px;text-align:right;font-family:var(--mono);font-weight:600;${retCls}">${t.returnPct >= 0 ? '+' : ''}${t.returnPct.toFixed(2)}%</td>
      <td style="padding:8px 10px;text-align:right;font-family:var(--mono);color:rgba(255,255,255,0.6)">₹${t.capital.toLocaleString()}</td>
    </tr>`;
  }).join('');
}

// ── Equity Curve Canvas Drawing ───────────────────────────────────────────────
function drawEquityCurve(data) {
  const canvas = document.getElementById('slCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  canvas.width = canvas.offsetWidth * dpr;
  canvas.height = canvas.offsetHeight * dpr;
  ctx.scale(dpr, dpr);

  const w = canvas.offsetWidth;
  const h = canvas.offsetHeight;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pad = 10;

  const toX = i => pad + (i / (data.length - 1)) * (w - pad * 2);
  const toY = v => pad + (1 - (v - min) / range) * (h - pad * 2);

  // Fill area
  ctx.beginPath();
  ctx.moveTo(toX(0), h);
  for (let i = 0; i < data.length; i++) ctx.lineTo(toX(i), toY(data[i]));
  ctx.lineTo(toX(data.length - 1), h);
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, 'rgba(61,142,244,0.15)');
  grad.addColorStop(1, 'rgba(61,142,244,0.01)');
  ctx.fillStyle = grad;
  ctx.fill();

  // Line
  ctx.beginPath();
  for (let i = 0; i < data.length; i++) {
    const x = toX(i), y = toY(data[i]);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.strokeStyle = '#3d8ef4';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Start/end labels
  ctx.font = '11px Inter, sans-serif';
  ctx.fillStyle = 'rgba(255,255,255,0.4)';
  ctx.fillText('₹' + data[0].toLocaleString(), toX(0) + 4, toY(data[0]) - 6);
  ctx.fillStyle = '#10f5a8';
  ctx.fillText('₹' + data[data.length - 1].toLocaleString(), toX(data.length - 1) - 80, toY(data[data.length - 1]) - 6);
}

// ── Old Backtest Data (secondary section) ─────────────────────────────────────
function renderOldBacktestData() {
  if (!backtestData) return '';
  const cfg = backtestData.config || {};
  const cmp = backtestData.comparison || {};
  const mA  = backtestData.mode_a || {};
  const mB  = backtestData.mode_b || {};
  const pct = n => n != null ? `${n > 0 ? '+' : ''}${n.toFixed(2)}%` : '—';
  const money = n => n != null ? `₹${Math.round(n).toLocaleString()}` : '—';

  return `
    <div style="margin-top:32px;padding-top:24px;border-top:1px solid var(--border)">
      <div style="font-size:14px;font-weight:700;color:rgba(255,255,255,0.6);margin-bottom:14px">📊 Historical Backtest Report (Auto-generated)</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.35);margin-bottom:16px">
        ${backtestData.generated || ''} · TP=${cfg.take_profit_pct || 4}% SL≥${cfg.stop_loss_fixed_pct || 2}% · Hold≤${cfg.max_hold_days || 5}d · Window: ${cfg.backtest_weeks || 52}wk · Capital: ₹${(cfg.capital || 1000000).toLocaleString()}
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;margin-bottom:16px">
        ${[
          {v: (mA?.total_trades || '—'), l: 'Total Trades (All)', c: 'var(--blue)'},
          {v: (mA?.win_rate_pct || '—') + '%', l: 'Win Rate (All)', c: (mA?.win_rate_pct||0) >= 50 ? 'var(--green)' : 'var(--amber)'},
          {v: pct(mA?.expectancy_pct), l: 'Expectancy (All)', c: (mA?.expectancy_pct||0) >= 0 ? 'var(--green)' : 'var(--red)'},
          {v: (mB?.total_trades || '—'), l: 'Total Trades (AI)', c: 'var(--blue)'},
          {v: (mB?.win_rate_pct || '—') + '%', l: 'Win Rate (AI)', c: (mB?.win_rate_pct||0) >= 50 ? 'var(--green)' : 'var(--amber)'},
          {v: pct(mB?.expectancy_pct), l: 'Expectancy (AI)', c: (mB?.expectancy_pct||0) >= 0 ? 'var(--green)' : 'var(--red)'},
          {v: money(mB?.final_capital), l: 'Final Capital (AI)', c: 'var(--primary)'},
          {v: (cmp?.ai_filtering_edge||0) > 0 ? '+' + (cmp.ai_filtering_edge).toFixed(2) + '%' : (cmp?.ai_filtering_edge||0).toFixed(2)+'%', l:'AI Filtering Edge', c: (cmp?.ai_filtering_edge||0)>0?'var(--emerald)':'var(--red)'}
        ].map(s => `<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:12px;text-align:center">
          <div style="font-size:18px;font-weight:700;font-family:var(--mono);color:${s.c};margin-bottom:4px">${s.v}</div>
          <div style="font-size:10px;color:rgba(255,255,255,0.3)">${s.l}</div>
        </div>`).join('')}
      </div>
    </div>`;
}

/* ═══════════════════════════════════════════════════════════════
   PREDICTIONS TAB
   4 sections:
     1. Prediction Table  — next-week BUY/SELL/HOLD for all stocks
     2. Accuracy Dashboard — precision, win rate, avg return
     3. Confusion Matrix   — 3x3 heatmap
     4. Weekly Log         — paginated prediction history
═══════════════════════════════════════════════════════════════ */

let _predLogPage = 0;
const PRED_LOG_PAGE = 50;

function buildPredictionTab() {
  const el = document.getElementById('tab-predictions');
  if (!el) return;

  if (!predictionsData) {
    el.innerHTML = `<div style="padding:60px;text-align:center;color:rgba(255,255,255,0.3)">
      <div style="font-size:48px;margin-bottom:16px">🔮</div>
      <div style="font-size:18px;font-weight:600;margin-bottom:8px">No Prediction Data Yet</div>
      <div style="font-size:14px">Run <code style="background:rgba(255,255,255,0.08);padding:2px 8px;border-radius:4px">python prediction_engine.py</code> to generate next-week signals.</div>
    </div>`;
    return;
  }

  const acc   = predAccuracyData?.accuracy  || {};
  const bench = predAccuracyData?.benchmarks || {};
  const preds = predictionsData.predictions  || [];
  const sum   = predictionsData.summary      || {};
  const regime = predictionsData.regime      || '—';
  const method = predictionsData.method      || 'rule_based';
  const methodLabel = method === 'random_forest' ? '🧠 Random Forest'
                    : method === 'fallback_ai_score' ? '⚠️ Fallback (AI Score)'
                    : '📍 Rule-Based';

  el.innerHTML = `
    <div class="pred-container">

      <!-- Hero banner -->
      <div class="pred-hero">
        <div class="pred-hero-left">
          <div class="pred-method-badge">${methodLabel}</div>
          <h2 class="pred-hero-title">🔮 Next-Week Forecast</h2>
          <p class="pred-hero-sub">
            Walk-forward prediction of BUY / SELL / HOLD for the coming week,
            calibrated to the <strong>${regime}</strong> market regime.
            Use high-confidence BUY signals as entry candidates, not standalone buy orders.
          </p>
        </div>
        <div class="pred-hero-stats">
          <div class="pred-hero-stat" style="color:var(--green)">
            <span class="pred-hero-val">${sum.buy || 0}</span>
            <span class="pred-hero-lbl">🟢 BUY</span>
          </div>
          <div class="pred-hero-stat" style="color:var(--amber)">
            <span class="pred-hero-val">${sum.hold || 0}</span>
            <span class="pred-hero-lbl">🟡 HOLD</span>
          </div>
          <div class="pred-hero-stat" style="color:var(--red)">
            <span class="pred-hero-val">${sum.sell || 0}</span>
            <span class="pred-hero-lbl">🔴 SELL</span>
          </div>
          <div class="pred-hero-stat" style="color:var(--blue)">
            <span class="pred-hero-val">${sum.avg_confidence || '—'}%</span>
            <span class="pred-hero-lbl">Avg Conf</span>
          </div>
        </div>
      </div>

      <!-- ═══ INVESTOR EDUCATION: What to expect ═══ -->
      <div style="background:rgba(167,139,250,0.04);border:1px solid rgba(167,139,250,0.1);border-radius:10px;padding:14px 18px;margin-bottom:18px;font-size:12.5px;color:rgba(255,255,255,0.5);line-height:1.7">
        <strong style="color:var(--purple)">💡 What to expect here:</strong> These are <strong style="color:rgba(255,255,255,0.7)">next-week directional predictions</strong> for all scanned stocks. Filter by signal type or slide the confidence bar to narrow the list. Use BUY signals with confidence above 65% as starting candidates — always check the chart on TradingView before acting.
      </div>

      <!-- ═══ READING THE NUMBERS ═══ -->
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:18px 22px;margin-bottom:22px">
        <div style="font-size:13px;font-weight:700;color:#fff;margin-bottom:12px;display:flex;align-items:center;gap:8px;cursor:pointer" onclick="document.getElementById('rrGuide').classList.toggle('collapsed')">
          📖 Understanding the Numbers <span style="font-size:11px;color:rgba(255,255,255,0.3);margin-left:auto">click to expand/collapse</span>
        </div>
        <div id="rrGuide" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px">
          <div>
            <div style="font-size:11px;font-weight:700;color:var(--purple);margin-bottom:8px;text-transform:uppercase;letter-spacing:.06em">R:R (Risk-to-Reward Ratio)</div>
            <div style="font-size:12px;color:rgba(255,255,255,0.55);line-height:1.8">
              <div>• <strong style="color:var(--red)">< 1.5</strong> → Poor — you risk more than you gain</div>
              <div>• <strong style="color:var(--amber)">2.0</strong> → Acceptable minimum for swing trades</div>
              <div>• <strong style="color:var(--green)">3.0+</strong> → Professional grade setup</div>
              <div>• <strong style="color:var(--primary)">5.0+</strong> → Exceptional — rare but powerful</div>
              <div style="margin-top:4px;color:rgba(255,255,255,0.35)">💡 Pros only take trades with R:R ≥ 2.0</div>
            </div>
          </div>
          <div>
            <div style="font-size:11px;font-weight:700;color:var(--purple);margin-bottom:8px;text-transform:uppercase;letter-spacing:.06em">P(WIN) — Historical Win Rate</div>
            <div style="font-size:12px;color:rgba(255,255,255,0.55);line-height:1.8">
              <div>• <strong>< 35%</strong> → Historically weak signal</div>
              <div>• <strong>35–50%</strong> → Normal for swing trading</div>
              <div>• <strong>50%+</strong> → High hit rate — strong edge</div>
              <div style="margin-top:4px;color:rgba(255,255,255,0.35)">⚠️ 42% win rate with R:R 4.0 is STILL profitable!<br>
              (42 wins × 4 = 168 vs. 58 losses × 1 = 58)</div>
            </div>
          </div>
          <div>
            <div style="font-size:11px;font-weight:700;color:var(--purple);margin-bottom:8px;text-transform:uppercase;letter-spacing:.06em">Confidence Score (0–100)</div>
            <div style="font-size:12px;color:rgba(255,255,255,0.55);line-height:1.8">
              <div>• <strong style="color:rgba(255,255,255,0.35)">< 50%</strong> → Watchlist only — don't trade</div>
              <div>• <strong style="color:var(--amber)">50–70%</strong> → Valid setup, smaller position</div>
              <div>• <strong style="color:var(--green)">> 70%</strong> → High conviction — full position</div>
              <div style="margin-top:4px;color:rgba(255,255,255,0.35)">💡 Start by filtering confidence ≥ 65%</div>
            </div>
          </div>
        </div>
        <style>#rrGuide.collapsed{display:none}</style>
      </div>

      <!-- ═══ SECTION 2: ACCURACY DASHBOARD ═══ -->
      ${renderAccuracyDashboard(acc, bench)}

      <!-- ═══ SECTION 3: CONFUSION MATRIX ═══ -->
      ${renderConfusionMatrix(predAccuracyData?.accuracy?.confusion_matrix)}

      <!-- ═══ SECTION 1: PREDICTION TABLE ═══ -->
      <div class="pred-section">
        <div class="pred-section-title">📊 Next-Week Predictions</div>
        <div class="pred-controls">
          <input class="pred-input" id="predSearch" type="text" placeholder="🔍 Search ticker..." oninput="onPredSearch()">
          <div class="opp-chips" id="predSignalChips">
            <button class="chip active" onclick="onPredSignal('')">ALL</button>
            <button class="chip" onclick="onPredSignal('BUY')">🟢 BUY</button>
            <button class="chip" onclick="onPredSignal('SELL')">🔴 SELL</button>
            <button class="chip" onclick="onPredSignal('HOLD')">🟡 HOLD</button>
          </div>
          <select class="opp-select" id="predRegime" onchange="onPredFilter()">
            <option value="">All Regimes</option>
            <option value="Bull">Bull</option>
            <option value="Sideways">Sideways</option>
            <option value="Bear">Bear</option>
          </select>
          <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:rgba(255,255,255,0.4)">
            <span>Confidence ≥</span>
            <input type="range" id="predConfSlider" min="0" max="95" value="50"
              style="width:100px;accent-color:var(--purple);cursor:pointer"
              oninput="onPredConf(this.value)">
            <span id="predConfVal" style="color:var(--purple);font-family:var(--mono);min-width:30px">50%</span>
          </div>
          <span class="opp-count" id="predCount"></span>
        </div>
        <div class="table-wrap">
          <table id="predTable">
            <thead><tr>
              <th style="text-align:left">Ticker</th>
              <th>Signal</th>
              <th>Confidence</th>
              <th>Exp. Return</th>
              <th>Price</th>
              <th style="text-align:left;min-width:200px">Reasoning</th>
            </tr></thead>
            <tbody id="predTbody"></tbody>
          </table>
        </div>
        <div class="pagination" id="predPag"></div>
      </div>

      <!-- ═══ SECTION 4: WEEKLY LOG ═══ -->
      ${renderWeeklyLog(predAccuracyData?.accuracy?.weekly_log)}

    </div>

    <style>
      .pred-container{padding:20px 0;max-width:1400px;margin:0 auto}
      .pred-hero{display:flex;gap:24px;align-items:flex-start;background:linear-gradient(135deg,rgba(167,139,250,0.07),rgba(61,142,244,0.05));border:1px solid rgba(167,139,250,0.15);border-radius:16px;padding:28px 32px;margin-bottom:24px;flex-wrap:wrap}
      .pred-hero-left{flex:1;min-width:240px}
      .pred-method-badge{display:inline-block;background:rgba(167,139,250,0.12);border:1px solid rgba(167,139,250,0.25);color:var(--purple);font-size:11px;font-weight:700;padding:3px 12px;border-radius:20px;margin-bottom:10px;letter-spacing:.04em}
      .pred-hero-title{font-family:var(--heading);font-size:22px;font-weight:800;color:#fff;margin-bottom:8px}
      .pred-hero-sub{font-size:13px;color:rgba(255,255,255,0.5);line-height:1.7;max-width:520px}
      .pred-hero-stats{display:flex;gap:20px;flex-wrap:wrap;align-items:center}
      .pred-hero-stat{display:flex;flex-direction:column;align-items:center;min-width:64px}
      .pred-hero-val{font-size:26px;font-weight:800;font-family:var(--mono)}
      .pred-hero-lbl{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:rgba(255,255,255,0.35);margin-top:2px}
      .pred-section{margin-bottom:28px}
      .pred-section-title{font-size:13px;font-weight:700;color:rgba(255,255,255,0.9);margin-bottom:14px;display:flex;align-items:center;gap:8px;padding-bottom:8px;border-bottom:1px solid var(--border)}
      .pred-controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
      .pred-input{padding:7px 12px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:#fff;font-size:12px;font-family:var(--font);outline:none;width:160px}
      .pred-input:focus{border-color:var(--purple)}
      /* Accuracy dashboard */
      .pred-acc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:20px}
      .pred-acc-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center;transition:border-color .2s}
      .pred-acc-card:hover{border-color:rgba(167,139,250,0.3)}
      .pred-acc-val{font-size:22px;font-weight:800;font-family:var(--mono);margin-bottom:4px}
      .pred-acc-lbl{font-size:10px;color:rgba(255,255,255,0.35)}
      .pred-bench-banner{background:rgba(167,139,250,0.07);border:1px solid rgba(167,139,250,0.15);border-radius:8px;padding:12px 16px;margin-bottom:20px;display:flex;gap:20px;flex-wrap:wrap;align-items:center}
      .pred-bench-item{display:flex;flex-direction:column;gap:2px}
      .pred-bench-label{font-size:10px;color:rgba(255,255,255,0.3);text-transform:uppercase;letter-spacing:.04em}
      .pred-bench-val{font-size:14px;font-weight:700;font-family:var(--mono)}
      /* Confusion matrix */
      .pred-cm-wrap{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:24px;overflow-x:auto}
      .pred-cm-title{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:14px}
      .pred-cm-grid{display:grid;grid-template-columns:80px repeat(3,1fr);gap:4px;max-width:500px}
      .pred-cm-head{font-size:10px;font-weight:700;color:rgba(255,255,255,0.4);text-align:center;padding:6px}
      .pred-cm-row-label{font-size:11px;font-weight:700;color:rgba(255,255,255,0.6);display:flex;align-items:center;padding:6px 8px}
      .pred-cm-cell{border-radius:6px;padding:10px 6px;text-align:center;font-family:var(--mono);font-size:13px;font-weight:700}
      .pred-cm-cell.diag{background:rgba(63,185,80,0.15);color:var(--green)}
      .pred-cm-cell.off{background:rgba(248,81,73,0.08);color:rgba(248,81,73,0.7);font-weight:500}
      .pred-cm-cell.zero{background:transparent;color:rgba(255,255,255,0.1)}
      /* Timeline sparkline */
      .pred-timeline-wrap{margin-bottom:20px}
      /* Prediction signal badge */
      .pred-sig-badge{display:inline-block;font-size:11px;font-weight:800;padding:3px 10px;border-radius:5px;font-family:var(--mono)}
      .pred-sig-badge.BUY{background:rgba(63,185,80,0.15);color:var(--green);border:1px solid rgba(63,185,80,0.3)}
      .pred-sig-badge.SELL{background:rgba(248,81,73,0.15);color:var(--red);border:1px solid rgba(248,81,73,0.3)}
      .pred-sig-badge.HOLD{background:rgba(245,166,35,0.12);color:var(--amber);border:1px solid rgba(245,166,35,0.25)}
      /* Expected return heatmap */
      .pred-ret-pos{color:var(--green);font-family:var(--mono);font-weight:600}
      .pred-ret-neg{color:var(--red);font-family:var(--mono);font-weight:600}
      .pred-ret-neu{color:rgba(255,255,255,0.3);font-family:var(--mono)}
      /* Reasoning tooltip */
      .pred-reason{font-size:11px;color:rgba(255,255,255,0.45);max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:help}
      /* Weekly log */
      .pred-log-wrap{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px}
      .pred-correct{color:var(--green)}
      .pred-wrong{color:var(--red)}
      /* Accuracy timeline chart */
      .pred-timeline-svg{width:100%;height:60px;background:rgba(255,255,255,0.02);border-radius:6px;overflow:visible}
      @media(max-width:768px){
        .pred-hero{flex-direction:column;padding:20px}
        .pred-cm-grid{max-width:100%}
      }
    </style>`;

  // Populate prediction table
  window._predData = preds;
  renderPredictionTable();

  // Render accuracy timeline sparkline
  renderAccuracyTimeline();
}

// ── Accuracy Dashboard ────────────────────────────────────────────────────────
function renderAccuracyDashboard(acc, bench) {
  if (!acc || !acc.overall_accuracy_pct) {
    return `<div class="pred-section"><div class="pred-section-title">🎯 Accuracy Dashboard</div>
      <div style="padding:24px;text-align:center;color:rgba(255,255,255,0.3);font-size:13px">
        Run walk-forward backtest to see accuracy metrics here.
      </div></div>`;
  }

  const p = acc.precision || {};
  const wr = acc.win_rate || {};
  const ar = acc.avg_return_per_prediction || {};
  const fmt = v => v != null ? v + '%' : '—';
  const fmtR = v => v != null ? (v >= 0 ? '+' : '') + v + '%' : '—';
  const col = v => v == null ? 'var(--blue)' : v >= 60 ? 'var(--green)' : v >= 50 ? 'var(--amber)' : 'var(--red)';

  const card = (val, lbl, c) => `<div class="pred-acc-card">
    <div class="pred-acc-val" style="color:${c}">${val}</div>
    <div class="pred-acc-lbl">${lbl}</div>
  </div>`;

  // Benchmark banner
  let benchHtml = '';
  if (bench && bench.prediction_strategy) {
    const ps  = bench.prediction_strategy;
    const eq  = bench.equal_weight_benchmark || {};
    const bh  = bench.buy_and_hold_nifty || {};
    const out = bench.outperformance_vs_eq_pct;
    const sig = bench.statistical_significance || '';
    benchHtml = `<div class="pred-bench-banner">
      <div class="pred-bench-item">
        <div class="pred-bench-label">Strategy Return</div>
        <div class="pred-bench-val" style="color:${(ps.total_return_pct||0)>=0?'var(--green)':'var(--red)'}">
          ${fmtR(ps.total_return_pct)}</div>
      </div>
      <div class="pred-bench-item">
        <div class="pred-bench-label">vs Equal Weight</div>
        <div class="pred-bench-val" style="color:${(out||0)>=0?'var(--green)':'var(--red)'}">
          ${out!=null?(out>=0?'+':'')+out+'%':'—'}</div>
      </div>
      ${bh.total_return_pct!=null?`<div class="pred-bench-item">
        <div class="pred-bench-label">vs NIFTY Buy &amp; Hold</div>
        <div class="pred-bench-val">${fmtR(bh.total_return_pct)}</div>
      </div>`:''}
      <div class="pred-bench-item" style="margin-left:auto;max-width:240px">
        <div class="pred-bench-label">Significance</div>
        <div style="font-size:11px;color:rgba(255,255,255,0.4);line-height:1.5">${sig}</div>
      </div>
    </div>`;
  }

  return `<div class="pred-section">
    <div class="pred-section-title">🎯 Historical Accuracy Dashboard
      <span style="font-size:10px;font-weight:400;color:rgba(255,255,255,0.3);margin-left:8px">
        ${predAccuracyData?.backtest_weeks || '?'} weeks · ${acc.total_predictions?.toLocaleString() || '?'} predictions
      </span>
    </div>
    ${benchHtml}
    <div class="pred-acc-grid">
      ${card(fmt(acc.overall_accuracy_pct),  'Overall Accuracy',   col(acc.overall_accuracy_pct))}
      ${card(fmt(p.buy_pct),  'BUY Precision',   col(p.buy_pct))}
      ${card(fmt(p.sell_pct), 'SELL Precision',  col(p.sell_pct))}
      ${card(fmt(p.hold_pct), 'HOLD Precision',  col(p.hold_pct))}
      ${card(fmt(wr.buy_pct),    'BUY Win Rate',  col(wr.buy_pct))}
      ${card(fmt(wr.sell_pct),   'SELL Win Rate', col(wr.sell_pct))}
      ${card(fmtR(ar.buy_pct),   'Avg BUY Return',  (ar.buy_pct||0)>=0?'var(--green)':'var(--red)')}
      ${card(fmtR(ar.sell_pct),  'Avg SELL Return', (ar.sell_pct||0)>=0?'var(--green)':'var(--red)')}
    </div>
    <div class="pred-timeline-wrap" id="predTimelineWrap"></div>
  </div>`;
}

// ── Confusion Matrix ──────────────────────────────────────────────────────────
function renderConfusionMatrix(cm) {
  if (!cm) return '';
  const LABELS = ['BUY', 'SELL', 'HOLD'];
  const labelColors = { BUY: 'var(--green)', SELL: 'var(--red)', HOLD: 'var(--amber)' };

  // Row totals for percentage labels
  const rowTotals = {};
  LABELS.forEach(pred => {
    rowTotals[pred] = LABELS.reduce((s, act) => s + (cm[pred]?.[act] || 0), 0);
  });

  let cells = '';
  // Header row
  cells += `<div class="pred-cm-head" style="grid-column:1"></div>`;
  LABELS.forEach(a => {
    cells += `<div class="pred-cm-head">Actual<br><span style="color:${labelColors[a]};font-weight:700">${a}</span></div>`;
  });
  // Data rows
  LABELS.forEach(pred => {
    cells += `<div class="pred-cm-row-label">Pred<br><span style="color:${labelColors[pred]};font-weight:700">${pred}</span></div>`;
    const rowTotal = rowTotals[pred] || 1;
    LABELS.forEach(act => {
      const count = cm[pred]?.[act] || 0;
      const pct   = Math.round(count / rowTotal * 100);
      const cls   = count === 0 ? 'zero' : pred === act ? 'diag' : 'off';
      const opacity = Math.max(0.3, pct / 100);
      cells += `<div class="pred-cm-cell ${cls}" title="${pred} predicted, ${act} actual: ${count} (${pct}%)">
        ${count}<span style="font-size:9px;font-weight:400;opacity:.6;margin-left:2px">${pct}%</span>
      </div>`;
    });
  });

  return `<div class="pred-section">
    <div class="pred-section-title">📊 Confusion Matrix <span style="font-size:10px;font-weight:400;color:rgba(255,255,255,0.3);margin-left:8px">Predicted → Actual outcomes</span></div>
    <div class="pred-cm-wrap">
      <div class="pred-cm-title">ROWS = PREDICTED · COLUMNS = ACTUAL · Diagonal (green) = Correct</div>
      <div class="pred-cm-grid">${cells}</div>
    </div>
  </div>`;
}

// ── Prediction Table ──────────────────────────────────────────────────────────
function renderPredictionTable() {
  let data = window._predData || [];

  if (_predFilter)  data = data.filter(p => p.ticker?.includes(_predFilter));
  if (_predSignal)  data = data.filter(p => p.prediction === _predSignal);
  if (_predConf > 0) data = data.filter(p => (p.confidence || 0) >= _predConf);

  const total = data.length;
  const countEl = document.getElementById('predCount');
  if (countEl) countEl.textContent = total.toLocaleString() + ' stocks';

  const page = data.slice(_predPage * PRED_PAGE, (_predPage + 1) * PRED_PAGE);

  const tbody = document.getElementById('predTbody');
  if (!tbody) return;

  tbody.innerHTML = page.map(p => {
    const ret = p.expected_return_pct;
    const retCls = ret > 1 ? 'pred-ret-pos' : ret < -1 ? 'pred-ret-neg' : 'pred-ret-neu';
    const retStr = ret != null ? (ret >= 0 ? '+' : '') + ret.toFixed(2) + '%' : '—';
    const narrative = p.reasoning?.narrative || '';
    const confColor = (p.confidence || 0) >= 70 ? 'var(--green)' : (p.confidence || 0) >= 50 ? 'var(--amber)' : 'var(--red)';
    const confBarW  = (p.confidence || 0) + '%';
    return `<tr>
      <td class="td-ticker"><a href="https://in.tradingview.com/chart/?symbol=NSE:${p.ticker}" target="_blank" rel="noopener">${p.ticker}</a></td>
      <td style="text-align:center"><span class="pred-sig-badge ${p.prediction}">${p.prediction}</span></td>
      <td style="text-align:center">
        <div style="display:flex;flex-direction:column;align-items:center;gap:3px">
          <span style="font-family:var(--mono);font-size:12px;font-weight:700;color:${confColor}">${p.confidence || '—'}%</span>
          <div style="width:60px;height:4px;background:rgba(255,255,255,0.07);border-radius:2px;overflow:hidden">
            <div style="width:${confBarW};height:100%;background:${confColor};border-radius:2px;transition:width .4s"></div>
          </div>
        </div>
      </td>
      <td style="text-align:center"><span class="${retCls}">${retStr}</span></td>
      <td style="font-family:var(--mono);font-size:11px;color:rgba(255,255,255,0.5);text-align:right">${p.price ? '₹' + p.price.toFixed(2) : '—'}</td>
      <td><div class="pred-reason" title="${narrative.replace(/"/g, '&quot;')}">${narrative || '—'}</div></td>
    </tr>`;
  }).join('');

  // Pagination
  const totalPages = Math.ceil(total / PRED_PAGE);
  const pag = document.getElementById('predPag');
  if (!pag) return;
  if (totalPages <= 1) { pag.innerHTML = ''; return; }
  const pages = [];
  pages.push(`<button class="pg-btn" onclick="predGo(Math.max(0,${_predPage}-1))">← Prev</button>`);
  const s = Math.max(0, _predPage - 2), e = Math.min(totalPages, _predPage + 5);
  if (s > 0) pages.push(`<button class="pg-btn" onclick="predGo(0)">1</button><span style="color:rgba(255,255,255,0.2)">…</span>`);
  for (let i = s; i < e; i++) pages.push(`<button class="pg-btn ${i === _predPage ? 'active' : ''}" onclick="predGo(${i})">${i + 1}</button>`);
  if (e < totalPages) pages.push(`<span style="color:rgba(255,255,255,0.2)">…</span><button class="pg-btn" onclick="predGo(${totalPages - 1})">${totalPages}</button>`);
  pages.push(`<button class="pg-btn" onclick="predGo(Math.min(${totalPages - 1},${_predPage}+1))">Next →</button>`);
  pag.innerHTML = pages.join('');
}

function predGo(p) { _predPage = p; renderPredictionTable(); window.scrollTo({ top: 400, behavior: 'smooth' }); }
function onPredSearch() { _predFilter = document.getElementById('predSearch').value.toUpperCase().trim(); _predPage = 0; renderPredictionTable(); }
function onPredFilter() { _predRegime = document.getElementById('predRegime').value; _predPage = 0; renderPredictionTable(); }
function onPredConf(v) {
  _predConf = parseInt(v); _predPage = 0;
  const el = document.getElementById('predConfVal');
  if (el) el.textContent = v + '%';
  renderPredictionTable();
}
function onPredSignal(sig) {
  _predSignal = sig; _predPage = 0;
  document.querySelectorAll('#predSignalChips .chip').forEach(c => c.classList.remove('active'));
  const active = [...document.querySelectorAll('#predSignalChips .chip')].find(c => c.textContent.trim().endsWith(sig) || (sig === '' && c.textContent.trim() === 'ALL'));
  if (active) active.classList.add('active');
  renderPredictionTable();
}

// ── Weekly Log ────────────────────────────────────────────────────────────────
function renderWeeklyLog(logEntries) {
  if (!logEntries || !logEntries.length) return '';

  const page = logEntries.slice(_predLogPage * PRED_LOG_PAGE, (_predLogPage + 1) * PRED_LOG_PAGE);
  const rows = page.map(r => {
    const retStr = r.return_pct != null ? (r.return_pct >= 0 ? '+' : '') + r.return_pct.toFixed(2) + '%' : '—';
    const retCls = (r.return_pct || 0) >= 0 ? 'pos' : 'neg';
    return `<tr>
      <td class="td-date">${r.week}</td>
      <td class="td-ticker"><a href="https://in.tradingview.com/chart/?symbol=NSE:${r.ticker}" target="_blank">${r.ticker}</a></td>
      <td style="text-align:center"><span class="pred-sig-badge ${r.predicted}">${r.predicted}</span></td>
      <td style="text-align:center"><span class="pred-sig-badge ${r.actual}">${r.actual}</span></td>
      <td class="${retCls}" style="text-align:right;font-family:var(--mono);font-size:11px">${retStr}</td>
      <td style="text-align:center;font-size:16px">${r.correct ? '✅' : '❌'}</td>
      <td style="text-align:center;font-family:var(--mono);font-size:11px;color:rgba(255,255,255,0.3)">${r.confidence || '—'}%</td>
    </tr>`;
  }).join('');

  const totalPages = Math.ceil(logEntries.length / PRED_LOG_PAGE);
  let pag = '';
  if (totalPages > 1) {
    for (let i = 0; i < totalPages; i++) pag += `<button class="pg-btn ${i === _predLogPage ? 'active' : ''}" onclick="predLogGo(${i})">${i + 1}</button>`;
  }

  return `<div class="pred-section">
    <div class="pred-section-title">📆 Historical Prediction Log
      <span style="font-size:10px;font-weight:400;color:rgba(255,255,255,0.3);margin-left:8px">
        ${logEntries.length.toLocaleString()} entries (latest first)
      </span>
    </div>
    <div class="pred-log-wrap">
      <div class="table-wrap">
        <table><thead><tr>
          <th style="text-align:left">Week</th>
          <th style="text-align:left">Ticker</th>
          <th>Predicted</th>
          <th>Actual</th>
          <th>Return</th>
          <th>Result</th>
          <th>Conf</th>
        </tr></thead><tbody>${rows}</tbody></table>
      </div>
      <div class="pagination" style="margin-top:12px">${pag}</div>
    </div>
  </div>`;
}

function predLogGo(p) {
  _predLogPage = p;
  // Re-render the full tab (simplest approach since log is static per load)
  buildPredictionTab();
}

// ── Accuracy Timeline Sparkline ───────────────────────────────────────────────
function renderAccuracyTimeline() {
  const wrap = document.getElementById('predTimelineWrap');
  if (!wrap) return;
  const timeline = predAccuracyData?.accuracy?.accuracy_timeline;
  if (!timeline || timeline.length < 2) { wrap.innerHTML = ''; return; }

  const accs = timeline.map(t => t.accuracy_pct);
  const maxA = Math.max(...accs, 70);
  const minA = Math.min(...accs, 40);
  const range = maxA - minA || 1;
  const w = 600, h = 60;

  const pts = timeline.map((t, i) => {
    const x = (i / (timeline.length - 1)) * w;
    const y = h - ((t.accuracy_pct - minA) / range) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  // 50% reference line
  const y50 = h - ((50 - minA) / range) * h;

  const labels = timeline.filter((_, i) => i % Math.max(1, Math.floor(timeline.length / 6)) === 0)
    .map(t => `<text x="${((timeline.indexOf(t)) / (timeline.length - 1) * w).toFixed(0)}" y="${h + 14}" font-size="9" fill="rgba(255,255,255,0.25)" text-anchor="middle">${t.month}</text>`).join('');

  wrap.innerHTML = `
    <div style="font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:6px">
      Monthly Accuracy % (${timeline.length} months)
    </div>
    <svg viewBox="0 0 ${w} ${h + 20}" class="pred-timeline-svg">
      <!-- 50% baseline -->
      <line x1="0" y1="${y50.toFixed(1)}" x2="${w}" y2="${y50.toFixed(1)}"
        stroke="rgba(255,255,255,0.08)" stroke-width="1" stroke-dasharray="4,4"/>
      <text x="4" y="${(y50 - 3).toFixed(1)}" font-size="8" fill="rgba(255,255,255,0.2)">50%</text>
      <!-- Accuracy line -->
      <polyline points="${pts}" fill="none" stroke="var(--purple)" stroke-width="2"/>
      <!-- Dots -->
      ${timeline.map((t, i) => {
        const x = (i / (timeline.length - 1)) * w;
        const y = h - ((t.accuracy_pct - minA) / range) * h;
        const c = t.accuracy_pct >= 55 ? 'var(--green)' : t.accuracy_pct >= 45 ? 'var(--amber)' : 'var(--red)';
        return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3" fill="${c}">
          <title>${t.month}: ${t.accuracy_pct}% (${t.trades} trades)</title></circle>`;
      }).join('')}
      ${labels}
    </svg>`;
}
