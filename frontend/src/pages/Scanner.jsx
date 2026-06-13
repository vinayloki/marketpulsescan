import React, { useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';

const TIMEFRAMES = [
  { key: 'daily',   label: 'Daily',   ma: '50 / 150 / 200 DMA' },
  { key: 'weekly',  label: 'Weekly',  ma: '10 / 30 / 40 WMA'   },
  { key: 'monthly', label: 'Monthly', ma: '12 / 24 / 48 MMA'   },
];

const COLUMNS = [
  { key: 'symbol',    label: 'Symbol',     sortable: true  },
  { key: 'name',      label: 'Company',    sortable: true  },
  { key: 'sector',    label: 'Sector',     sortable: true  },
  { key: 'exchange',  label: 'Exchange',   sortable: false },
  { key: 'score',     label: 'Score',      sortable: true  },
  { key: 'rs_rating', label: 'RS Rating',  sortable: true  },
  { key: 'price',     label: 'Price ₹',    sortable: true  },
  { key: 'sma_fast',  label: 'Fast MA',    sortable: false },
  { key: 'sma_slow',  label: 'Slow MA',    sortable: false },
  { key: 'ma_rising', label: 'MA Rising',  sortable: false },
];

function SortArrow({ dir }) {
  if (!dir) return <span className="sort-arrow neutral">⇅</span>;
  return <span className="sort-arrow active">{dir === 'asc' ? '↑' : '↓'}</span>;
}

function ConditionDot({ value }) {
  return (
    <span
      style={{
        display: 'inline-block',
        width: 10,
        height: 10,
        borderRadius: '50%',
        background: value ? 'var(--accent-green)' : 'var(--accent-red)',
        boxShadow: value ? '0 0 6px var(--accent-green)' : 'none',
      }}
      title={value ? 'Yes' : 'No'}
    />
  );
}

function ScoreBadge({ score }) {
  const cls = score >= 90 ? 'green' : score >= 75 ? 'blue' : 'yellow';
  return <span className={`badge ${cls}`}>{score?.toFixed(0) ?? '—'}</span>;
}

function SkeletonRow() {
  return (
    <tr className="skeleton-row">
      {COLUMNS.map((c) => (
        <td key={c.key}><div className="skeleton-cell" /></td>
      ))}
    </tr>
  );
}

function Scanner() {
  const [timeframe, setTimeframe]   = useState('daily');
  const [data, setData]             = useState([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState(null);
  const [search, setSearch]         = useState('');
  const [sortKey, setSortKey]       = useState('score');
  const [sortDir, setSortDir]       = useState('desc');
  const [page, setPage]             = useState(1);
  const PAGE_SIZE = 50;

  const fetchData = useCallback((tf) => {
    setLoading(true);
    setError(null);
    axios
      .get(`/api/scanner/stage2?timeframe=${tf}&limit=500`)
      .then((res) => {
        setData(res.data.data || []);
        setLoading(false);
      })
      .catch((err) => {
        setError('Could not fetch scanner data. Is the backend running?');
        setData([]);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    fetchData(timeframe);
    setPage(1);
  }, [timeframe, fetchData]);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
    setPage(1);
  };

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return data.filter(
      (s) =>
        s.symbol?.toLowerCase().includes(q) ||
        s.name?.toLowerCase().includes(q) ||
        s.sector?.toLowerCase().includes(q),
    );
  }, [data, search]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const av = a[sortKey] ?? '';
      const bv = b[sortKey] ?? '';
      if (av < bv) return sortDir === 'asc' ? -1 : 1;
      if (av > bv) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filtered, sortKey, sortDir]);

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  const paginated  = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const activeTf   = TIMEFRAMES.find((t) => t.key === timeframe);

  return (
    <div>
      {/* ── Header ── */}
      <div className="scanner-header">
        <div>
          <h2>Stage 2 Scanner</h2>
          <p className="subtext">
            Stan Weinstein Stage 2 / Minervini Trend Template — NSE &amp; BSE
          </p>
        </div>
        <div className="scanner-meta">
          {!loading && (
            <span className="badge blue">{filtered.length} stocks</span>
          )}
        </div>
      </div>

      {/* ── Timeframe Tabs ── */}
      <div className="timeframe-tabs">
        {TIMEFRAMES.map((tf) => (
          <button
            key={tf.key}
            className={`tf-tab ${timeframe === tf.key ? 'active' : ''}`}
            onClick={() => setTimeframe(tf.key)}
          >
            <span className="tf-label">{tf.label}</span>
            <span className="tf-ma">{tf.ma}</span>
          </button>
        ))}
      </div>

      {/* ── Search ── */}
      <div className="scanner-controls">
        <div className="search-wrapper">
          <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="text"
            className="search-input"
            placeholder="Search symbol, company or sector…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
          {search && (
            <button className="search-clear" onClick={() => { setSearch(''); setPage(1); }}>✕</button>
          )}
        </div>
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {/* ── Table ── */}
      <div className="card table-card">
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th className="th-rank">#</th>
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    className={col.sortable ? 'sortable' : ''}
                    onClick={col.sortable ? () => handleSort(col.key) : undefined}
                  >
                    {col.label}
                    {col.sortable && <SortArrow dir={sortKey === col.key ? sortDir : null} />}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 10 }).map((_, i) => <SkeletonRow key={i} />)
                : paginated.length === 0
                ? (
                  <tr>
                    <td colSpan={COLUMNS.length + 1} className="empty-state">
                      {search ? 'No stocks match your search.' : 'No Stage 2 stocks found. Run the scanner to populate results.'}
                    </td>
                  </tr>
                )
                : paginated.map((stock, idx) => (
                  <tr key={stock.symbol} className="data-row">
                    <td className="td-rank">{(page - 1) * PAGE_SIZE + idx + 1}</td>
                    <td className="td-symbol">{stock.symbol}</td>
                    <td className="td-name">{stock.name}</td>
                    <td>{stock.sector}</td>
                    <td>
                      <span className={`badge ${stock.exchange === 'BSE' ? 'yellow' : 'blue'}`} style={{ fontSize: '0.7rem' }}>
                        {stock.exchange}
                      </span>
                    </td>
                    <td><ScoreBadge score={stock.score} /></td>
                    <td className="td-rs">{stock.rs_rating?.toFixed(1) ?? '—'}</td>
                    <td className="td-price">₹{stock.price?.toLocaleString('en-IN', { maximumFractionDigits: 2 }) ?? '—'}</td>
                    <td className="td-ma">₹{stock.sma_fast?.toLocaleString('en-IN', { maximumFractionDigits: 2 }) ?? '—'}</td>
                    <td className="td-ma">₹{stock.sma_slow?.toLocaleString('en-IN', { maximumFractionDigits: 2 }) ?? '—'}</td>
                    <td style={{ textAlign: 'center' }}><ConditionDot value={stock.ma_rising} /></td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Pagination ── */}
      {totalPages > 1 && (
        <div className="pagination">
          <button className="page-btn" disabled={page === 1} onClick={() => setPage(1)}>«</button>
          <button className="page-btn" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>‹</button>
          <span className="page-info">Page {page} of {totalPages}</span>
          <button className="page-btn" disabled={page === totalPages} onClick={() => setPage((p) => p + 1)}>›</button>
          <button className="page-btn" disabled={page === totalPages} onClick={() => setPage(totalPages)}>»</button>
        </div>
      )}
    </div>
  );
}

export default Scanner;
