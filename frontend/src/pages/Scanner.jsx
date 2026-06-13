import React, { useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';
import TradingViewChart from '../components/TradingViewChart';

// ─── External links ───────────────────────────────────────────────────────────
function tvSymbol(symbol, exchange) {
  const exch  = (exchange || 'NSE').toUpperCase();
  const clean = symbol.replace(/\.NS$|\.BO$/i, '');
  return `${exch}:${clean}`;           // e.g. "NSE:APOLLOPIPE" for the widget
}
function tvUrl(symbol, exchange) {
  const clean = symbol.replace(/\.NS$|\.BO$/i, '');
  const exch  = (exchange || 'NSE').toUpperCase();
  return `https://in.tradingview.com/chart/kkc9tJsQ/?symbol=${exch}:${clean}`;
}
function screenerUrl(symbol) {
  const clean = symbol.replace(/\.NS$|\.BO$/i, '');
  return `https://www.screener.in/company/${clean}/`;
}
function ExternalLinks({ symbol, exchange }) {
  return (
    <span className="ext-links">
      <a href={tvUrl(symbol, exchange)} target="_blank" rel="noreferrer" className="ext-link tv" title="Open TradingView">
        <svg viewBox="0 0 24 24" fill="none" width="13" height="13" stroke="currentColor" strokeWidth="2">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
        TV
      </a>
      <a href={screenerUrl(symbol)} target="_blank" rel="noreferrer" className="ext-link sc" title="Open Screener.in">
        <svg viewBox="0 0 24 24" fill="none" width="13" height="13" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        SC
      </a>
    </span>
  );
}

// ─── Chart slide-out panel ──────────────────────────────────────────────────────
function ChartPanel({ stock, onClose }) {
  if (!stock) return null;
  const sym = tvSymbol(stock.symbol || stock.ticker, stock.exchange);
  return (
    <div className="chart-overlay" onClick={onClose}>
      <div className="chart-panel" onClick={(e) => e.stopPropagation()}>
        <div className="chart-panel-header">
          <div>
            <span className="chart-panel-symbol">{stock.symbol || stock.ticker}</span>
            <span className="chart-panel-name">{stock.name}</span>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <a href={tvUrl(stock.symbol || stock.ticker, stock.exchange)}
               target="_blank" rel="noreferrer" className="ext-link tv">Open full chart ↗</a>
            <a href={screenerUrl(stock.symbol || stock.ticker)}
               target="_blank" rel="noreferrer" className="ext-link sc">Screener.in ↗</a>
            <button className="chart-close-btn" onClick={onClose}>✕</button>
          </div>
        </div>
        <div className="chart-panel-body">
          <TradingViewChart symbol={sym} theme="dark" />
        </div>
      </div>
    </div>
  );
}

// ─── View modes ───────────────────────────────────────────────────────────────
const VIEWS = [
  { key: 'market',  label: '🌐 All NSE/BSE', sub: '3,000+ stocks with returns' },
  { key: 'stage2',  label: '📈 Stage 2',      sub: 'Weinstein / Minervini filter' },
];

const STAGE2_TF = [
  { key: 'daily',   label: 'Daily',   ma: '50 / 150 / 200 DMA' },
  { key: 'weekly',  label: 'Weekly',  ma: '10 / 30 / 40 WMA' },
  { key: 'monthly', label: 'Monthly', ma: '12 / 24 / 48 MMA' },
];

const RETURN_TF = ['1W', '2W', '1M', '3M', '6M', '12M'];

const MCAP_OPTIONS = [
  { key: '',  label: 'All Cap' },
  { key: 'L', label: 'Large Cap' },
  { key: 'M', label: 'Mid Cap' },
  { key: 'S', label: 'Small Cap' },
];

const PAGE_SIZE = 100;

// ─── Helpers ──────────────────────────────────────────────────────────────────
function SortArrow({ dir }) {
  if (!dir) return <span className="sort-arrow neutral">⇅</span>;
  return <span className="sort-arrow active">{dir === 'asc' ? '↑' : '↓'}</span>;
}

function ReturnCell({ value }) {
  if (value == null || value === 0) return <span className="ret-zero">—</span>;
  const cls = value > 0 ? 'green' : 'red';
  return (
    <span className={`ret-val ${cls}`}>
      {value > 0 ? '+' : ''}{value.toFixed(2)}%
    </span>
  );
}

function ScoreBadge({ score }) {
  const cls = score >= 90 ? 'green' : score >= 75 ? 'blue' : 'yellow';
  return <span className={`badge ${cls}`}>{score?.toFixed(0) ?? '—'}</span>;
}

function McapBadge({ code }) {
  const map = { L: ['blue', 'Large'], M: ['purple', 'Mid'], S: ['yellow', 'Small'] };
  const [cls, label] = map[code] || ['', code || '—'];
  return <span className={`badge ${cls}`} style={{ fontSize: '0.68rem' }}>{label}</span>;
}

function ConditionDot({ value }) {
  return (
    <span style={{
      display: 'inline-block', width: 9, height: 9, borderRadius: '50%',
      background: value ? 'var(--accent-green)' : 'var(--accent-red)',
      boxShadow: value ? '0 0 5px var(--accent-green)' : 'none',
    }} title={value ? 'Yes' : 'No'} />
  );
}

function SkeletonRow({ cols }) {
  return (
    <tr className="skeleton-row">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i}><div className="skeleton-cell" /></td>
      ))}
    </tr>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
function Scanner() {
  const [view, setView]             = useState('market');
  const [stage2Tf, setStage2Tf]     = useState('daily');
  const [returnTf, setReturnTf]     = useState('1M');
  const [mcapFilter, setMcapFilter] = useState('');
  const [search, setSearch]         = useState('');
  const [sortKey, setSortKey]       = useState(null);
  const [sortDir, setSortDir]       = useState('desc');
  const [page, setPage]             = useState(1);
  const [data, setData]             = useState([]);
  const [total, setTotal]           = useState(0);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState(null);
  const [selectedStock, setSelectedStock] = useState(null);  // chart panel

  // ── Fetch ──────────────────────────────────────────────────────────────────
  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);

    let url;
    if (view === 'market') {
      url = `${import.meta.env.BASE_URL}../scan_results/api/market.json`;
    } else {
      url = `${import.meta.env.BASE_URL}../scan_results/api/stage2_${stage2Tf}.json`;
    }

    axios.get(url)
      .then((res) => {
        setData(res.data.data || []);
        setTotal(res.data.total || res.data.count || 0);
        setLoading(false);
        setPage(1);
      })
      .catch(() => {
        setError('Could not reach the backend. Is the FastAPI server running on port 8000?');
        setData([]);
        setLoading(false);
      });
  }, [view, stage2Tf, returnTf, mcapFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ── Sort & Filter (client side) ────────────────────────────────────────────
  const filtered = useMemo(() => {
    let result = data;
    
    // Serverless Market filters (applied client-side now)
    if (view === 'market' && mcapFilter) {
      result = result.filter(s => s.mcap_code === mcapFilter);
    }
    
    const q = search.toLowerCase();
    if (q) {
      result = result.filter(
        (s) =>
          (s.symbol || s.ticker || '').toLowerCase().includes(q) ||
          (s.name || '').toLowerCase().includes(q) ||
          (s.sector || '').toLowerCase().includes(q),
      );
    }
    return result;
  }, [data, search, view, mcapFilter]);

  const sorted = useMemo(() => {
    let sortK = sortKey;
    let sortD = sortDir;
    
    // Serverless Market default sort (applied client-side)
    if (view === 'market' && !sortKey) {
      const tfMap = { '1W': 'ret_1w', '2W': 'ret_2w', '1M': 'ret_1m', '3M': 'ret_3m', '6M': 'ret_6m', '12M': 'ret_12m' };
      sortK = tfMap[returnTf] || 'ret_1m';
      sortD = 'desc';
    }
    
    if (!sortK) return filtered;
    return [...filtered].sort((a, b) => {
      const av = a[sortK] ?? (typeof a[sortK] === 'number' ? -Infinity : '');
      const bv = b[sortK] ?? (typeof b[sortK] === 'number' ? -Infinity : '');
      if (av < bv) return sortD === 'asc' ? -1 : 1;
      if (av > bv) return sortD === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filtered, sortKey, sortDir, view, returnTf]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const paginated  = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleSort = (key) => {
    if (sortKey === key) setSortDir((d) => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
    setPage(1);
  };

  const isMarket = view === 'market';

  // ── Market columns ──────────────────────────────────────────────────────────
  const marketCols = [
    { key: 'symbol',   label: 'Symbol',   sortable: true  },
    { key: 'name',     label: 'Company',  sortable: true  },
    { key: 'sector',   label: 'Sector',   sortable: true  },
    { key: 'mcap_code',label: 'Cap',      sortable: false },
    { key: 'exchange', label: 'Exchange', sortable: false },
    { key: 'price',    label: 'Price ₹',  sortable: true  },
    { key: 'ret_1w',   label: '1W %',     sortable: true  },
    { key: 'ret_2w',   label: '2W %',     sortable: true  },
    { key: 'ret_1m',   label: '1M %',     sortable: true  },
    { key: 'ret_3m',   label: '3M %',     sortable: true  },
    { key: 'ret_6m',   label: '6M %',     sortable: true  },
    { key: 'ret_12m',  label: '12M %',    sortable: true  },
  ];

  // ── Stage 2 columns ─────────────────────────────────────────────────────────
  const stage2Cols = [
    { key: 'symbol',    label: 'Symbol',   sortable: true  },
    { key: 'name',      label: 'Company',  sortable: true  },
    { key: 'sector',    label: 'Sector',   sortable: true  },
    { key: 'exchange',  label: 'Exch',     sortable: false },
    { key: 'score',     label: 'Score',    sortable: true  },
    { key: 'rs_rating', label: 'RS',       sortable: true  },
    { key: 'price',     label: 'Price ₹',  sortable: true  },
    { key: 'sma_fast',  label: 'Fast MA',  sortable: false },
    { key: 'sma_slow',  label: 'Slow MA',  sortable: false },
    { key: 'high_52w',  label: '52W High', sortable: false },
    { key: 'ma_rising', label: 'MA↑',      sortable: false },
  ];

  const cols = isMarket ? marketCols : stage2Cols;

  return (
    <div>
      {/* ── View Switcher ── */}
      <div className="scanner-header">
        <div>
          <h2>Scanner</h2>
          <p className="subtext">NSE &amp; BSE — {total.toLocaleString('en-IN')} stocks</p>
        </div>
        <div className="view-switcher">
          {VIEWS.map((v) => (
            <button key={v.key} className={`view-btn ${view === v.key ? 'active' : ''}`}
              onClick={() => { setView(v.key); setPage(1); setSortKey(null); }}>
              <span>{v.label}</span>
              <small>{v.sub}</small>
            </button>
          ))}
        </div>
      </div>

      {/* ── Controls Row ── */}
      <div className="controls-row">
        {/* Search */}
        <div className="search-wrapper">
          <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          <input type="text" className="search-input"
            placeholder="Symbol, company, sector…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
          {search && <button className="search-clear" onClick={() => { setSearch(''); setPage(1); }}>✕</button>}
        </div>

        {/* Market-specific controls */}
        {isMarket && (
          <>
            <div className="tf-pill-group">
              {RETURN_TF.map((tf) => (
                <button key={tf} className={`tf-pill ${returnTf === tf ? 'active' : ''}`}
                  onClick={() => setReturnTf(tf)}>
                  {tf}
                </button>
              ))}
            </div>
            <div className="tf-pill-group">
              {MCAP_OPTIONS.map((m) => (
                <button key={m.key} className={`tf-pill ${mcapFilter === m.key ? 'active' : ''}`}
                  onClick={() => { setMcapFilter(m.key); setPage(1); }}>
                  {m.label}
                </button>
              ))}
            </div>
          </>
        )}

        {/* Stage 2 timeframe tabs */}
        {!isMarket && (
          <div className="timeframe-tabs" style={{ margin: 0 }}>
            {STAGE2_TF.map((tf) => (
              <button key={tf.key} className={`tf-tab ${stage2Tf === tf.key ? 'active' : ''}`}
                onClick={() => { setStage2Tf(tf.key); setPage(1); }}>
                <span className="tf-label">{tf.label}</span>
                <span className="tf-ma">{tf.ma}</span>
              </button>
            ))}
          </div>
        )}

        {/* Count badge */}
        {!loading && (
          <span className="badge blue" style={{ marginLeft: 'auto', whiteSpace: 'nowrap' }}>
            {filtered.length.toLocaleString('en-IN')} results
          </span>
        )}
      </div>

      {/* ── Error ── */}
      {error && <div className="error-banner">⚠️ {error}</div>}

      {/* ── Table ── */}
      <div className="card table-card">
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th className="th-rank">#</th>
                {cols.map((col) => (
                  <th key={col.key}
                    className={col.sortable ? 'sortable' : ''}
                    onClick={col.sortable ? () => handleSort(col.key) : undefined}>
                    {col.label}
                    {col.sortable && <SortArrow dir={sortKey === col.key ? sortDir : null} />}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 15 }).map((_, i) => <SkeletonRow key={i} cols={cols.length + 1} />)
                : paginated.length === 0
                  ? (
                    <tr><td colSpan={cols.length + 1} className="empty-state">
                      {search ? 'No stocks match your search.' : 'No data found. Is the scanner running?'}
                    </td></tr>
                  )
                  : paginated.map((stock, idx) => {
                    const rank = (page - 1) * PAGE_SIZE + idx + 1;
                    return isMarket
                      ? <MarketRow key={stock.ticker} stock={stock} rank={rank} onClick={() => setSelectedStock(stock)} />
                      : <Stage2Row key={stock.symbol} stock={stock} rank={rank} onClick={() => setSelectedStock(stock)} />;
                  })
              }
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Pagination ── */}
      {totalPages > 1 && (
        <div className="pagination">
          <button className="page-btn" disabled={page === 1} onClick={() => setPage(1)}>«</button>
          <button className="page-btn" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>‹</button>
          <span className="page-info">Page {page} of {totalPages} ({sorted.length.toLocaleString('en-IN')} stocks)</span>
          <button className="page-btn" disabled={page === totalPages} onClick={() => setPage((p) => p + 1)}>›</button>
          <button className="page-btn" disabled={page === totalPages} onClick={() => setPage(totalPages)}>»</button>
        </div>
      )}

      {/* ── Chart Panel Overlay ── */}
      {selectedStock && (
        <ChartPanel stock={selectedStock} onClose={() => setSelectedStock(null)} />
      )}
    </div>
  );
}

// ─── Row components ──────────────────────────────────────────────────────────

function MarketRow({ stock, rank, onClick }) {
  return (
    <tr className="data-row" onClick={onClick} style={{ cursor: 'pointer' }}>
      <td className="td-rank">{rank}</td>
      <td className="td-symbol">
        {stock.symbol}
        <ExternalLinks symbol={stock.symbol} exchange={stock.exchange} />
      </td>
      <td className="td-name">{stock.name}</td>
      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{stock.sector}</td>
      <td><McapBadge code={stock.mcap_code} /></td>
      <td>
        <span className={`badge ${stock.exchange === 'BSE' ? 'yellow' : 'blue'}`} style={{ fontSize: '0.68rem' }}>
          {stock.exchange}
        </span>
      </td>
      <td className="td-price">₹{stock.price?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
      <td><ReturnCell value={stock.ret_1w} /></td>
      <td><ReturnCell value={stock.ret_2w} /></td>
      <td><ReturnCell value={stock.ret_1m} /></td>
      <td><ReturnCell value={stock.ret_3m} /></td>
      <td><ReturnCell value={stock.ret_6m} /></td>
      <td><ReturnCell value={stock.ret_12m} /></td>
    </tr>
  );
}

function Stage2Row({ stock, rank, onClick }) {
  return (
    <tr className="data-row" onClick={onClick} style={{ cursor: 'pointer' }}>
      <td className="td-rank">{rank}</td>
      <td className="td-symbol">
        {stock.symbol}
        <ExternalLinks symbol={stock.symbol} exchange={stock.exchange} />
      </td>
      <td className="td-name">{stock.name}</td>
      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{stock.sector}</td>
      <td>
        <span className={`badge ${stock.exchange === 'BSE' ? 'yellow' : 'blue'}`} style={{ fontSize: '0.68rem' }}>
          {stock.exchange}
        </span>
      </td>
      <td><ScoreBadge score={stock.score} /></td>
      <td className="td-rs">{stock.rs_rating?.toFixed(1) ?? '—'}</td>
      <td className="td-price">₹{stock.price?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
      <td className="td-ma">₹{stock.sma_fast?.toLocaleString('en-IN', { maximumFractionDigits: 2 }) ?? '—'}</td>
      <td className="td-ma">₹{stock.sma_slow?.toLocaleString('en-IN', { maximumFractionDigits: 2 }) ?? '—'}</td>
      <td className="td-ma">₹{stock.high_52w?.toLocaleString('en-IN', { maximumFractionDigits: 2 }) ?? '—'}</td>
      <td style={{ textAlign: 'center' }}><ConditionDot value={stock.ma_rising} /></td>
    </tr>
  );
}

export default Scanner;
