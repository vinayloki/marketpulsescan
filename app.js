/**
 * SWINGSCAN INDIA — MAIN APP
 * 3 tabs: Top Movers (with fundamentals), Full Scan (2200+), News
 * Auto-loads on page open. No button needed.
 */

/* ═══════════════════════════════════════════════════════════════
   GLOBALS
═══════════════════════════════════════════════════════════════ */
let summaryData    = null;   // latest_scan_summary.json
let fullScanData   = [];     // full_summary.json → stocks[]
let fundamentals   = {};     // fundamentals.json → keyed by symbol
let newsData       = [];     // daily_news.json
let currentTf      = '1M';

// Full Scan table state
let _fsSortCol = '1M', _fsSortAsc = false, _fsFilter = '', _fsTfFilter = '', _fsPage = 0;
const FS_PAGE = 100;

// Top Movers filter state
let _tmSearch = '', _tmSector = '', _tmPe = '', _tmMcap = '';

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
    const [summRes, fullRes, fundRes, newsRes] = await Promise.allSettled([
      fetch('scan_results/latest_scan_summary.json'),
      fetch('scan_results/full_summary.json'),
      fetch('scan_results/fundamentals.json'),
      fetch('scan_results/daily_news.json'),
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

    buildDashboard();
    document.getElementById('loadScreen').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';

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
  const scanDate   = summaryData?.scan_date || '—';
  const stockCount = fullScanData.length || summaryData?.total_stocks_scanned || '—';
  document.getElementById('hScanDate').textContent   = scanDate;
  document.getElementById('hStockCount').textContent  = stockCount;
  document.getElementById('footerDate').textContent   = scanDate;

  buildStatsRow();
  buildTopMovers();
  buildFullScan();
  buildNews();
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
  const fundCount = Object.keys(fundamentals).length;

  const mb1W = summaryData?.market_breadth?.['1W'];
  const adRatio = mb1W ? mb1W.advance_decline_ratio.toFixed(1) : '—';

  const sc = (v, l, c) => `<div class="stat-card"><div class="sv ${c}">${v}</div><div class="sl">${l}</div></div>`;
  el.innerHTML = [
    sc(total,     'Stocks Scanned', 'col-blue'),
    sc(g1W,       '1W Gainers',     'col-green'),
    sc(g1M,       '1M Gainers',     'col-green'),
    sc(l1M,       '1M Losers',      'col-red'),
    sc(multi,     '12M > 100%',     'col-purple'),
    sc(adRatio,   '1W A/D Ratio',   'col-emerald'),
    sc(fundCount, 'With Fundamentals', 'col-amber'),
  ].join('');
}

/* ═══════════════════════════════════════════════════════════════
   TOP MOVERS (with fundamentals)
═══════════════════════════════════════════════════════════════ */
function buildTopMovers() {
  // Collect unique top movers across all timeframes
  const seen = new Set();
  const movers = [];

  for (const tf of TFS) {
    const sorted = fullScanData
      .filter(s => s[tf] != null)
      .sort((a, b) => (b[tf] || 0) - (a[tf] || 0));

    for (const s of sorted.slice(0, 20)) {
      if (!seen.has(s.t)) {
        seen.add(s.t);
        movers.push(s);
      }
    }
  }

  // Sort by best 1M performance by default
  movers.sort((a, b) => (b['1M'] || 0) - (a['1M'] || 0));

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
    data = data.filter(s => {
      const mc = fundamentals[s.t]?.mcap;
      if (!mc) return false;
      if (_tmMcap === 'large') return mc >= 20000;
      if (_tmMcap === 'mid')   return mc >= 5000 && mc < 20000;
      if (_tmMcap === 'small') return mc < 5000;
      return true;
    });
  }

  document.getElementById('tmCount').textContent = `${data.length} stocks`;

  const grid = document.getElementById('moversGrid');
  if (data.length === 0) {
    grid.innerHTML = `<div style="padding:40px;text-align:center;color:rgba(255,255,255,0.3);grid-column:1/-1;">No stocks match your filters.</div>`;
    return;
  }

  grid.innerHTML = data.map((s, i) => {
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
        <div class="mc-rank">#${i+1}</div>
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
}

function onTmSearch() { _tmSearch = document.getElementById('tmSearch').value.toUpperCase(); renderTopMovers(); }
function onTmSector() { _tmSector = document.getElementById('tmSector').value; renderTopMovers(); }
function onTmPe()     { _tmPe     = document.getElementById('tmPe').value;     renderTopMovers(); }
function onTmMcap()   { _tmMcap   = document.getElementById('tmMcap').value;   renderTopMovers(); }

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
