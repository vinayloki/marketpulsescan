import React, { useState, useEffect } from 'react';
import axios from 'axios';

const TF_PERF_OPTIONS = ['1W', '2W', '1M', '3M', '6M', '12M'];

function StatCard({ label, value, sub, color = 'blue', icon }) {
  return (
    <div className="card stat-card">
      <div className="stat-icon" style={{ color: `var(--accent-${color})` }}>{icon}</div>
      <div className="stat-body">
        <p className="stat-label">{label}</p>
        <h2 className="stat-value" style={{ color: `var(--accent-${color})` }}>{value}</h2>
        {sub && <p className="stat-sub">{sub}</p>}
      </div>
    </div>
  );
}

function BreadthBar({ label, advancing, declining, unchanged }) {
  const total = (advancing + declining + unchanged) || 1;
  return (
    <div className="breadth-row">
      <span className="breadth-label">{label}</span>
      <div className="breadth-bar-track">
        <div className="breadth-seg green"  style={{ width: `${(advancing / total) * 100}%` }} title={`Advancing: ${advancing}`} />
        <div className="breadth-seg red"    style={{ width: `${(declining / total) * 100}%` }} title={`Declining: ${declining}`} />
        <div className="breadth-seg muted"  style={{ width: `${(unchanged / total) * 100}%` }} title={`Unchanged: ${unchanged}`} />
      </div>
      <span className="breadth-count green">{advancing}↑</span>
      <span className="breadth-count red">{declining}↓</span>
    </div>
  );
}

function Dashboard() {
  const [summary, setSummary]         = useState(null);
  const [topPerf, setTopPerf]         = useState([]);
  const [perfTf, setPerfTf]           = useState('1M');
  const [loading, setLoading]         = useState(true);
  const [loadingPerf, setLoadingPerf] = useState(false);

  useEffect(() => {
    axios.get('/api/scanner/summary')
      .then((res) => { setSummary(res.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    setLoadingPerf(true);
    axios.get(`/api/scanner/top-performers?timeframe=${perfTf}&limit=10`)
      .then((res) => { setTopPerf(res.data.data || []); setLoadingPerf(false); })
      .catch(() => setLoadingPerf(false));
  }, [perfTf]);

  const regime    = summary?.market_regime  || {};
  const scan      = summary?.scan_summary   || {};
  const counts    = summary?.stage2_counts  || {};
  const opps      = summary?.opportunities  || [];
  const breadth   = scan.market_breadth     || {};
  const regimeVal = regime.regime           || '—';
  const regimeColor = regimeVal === 'Bull' ? 'green' : regimeVal === 'Bear' ? 'red' : 'yellow';

  return (
    <div>
      <div className="page-header">
        <h2>Market Overview</h2>
        <p className="subtext">
          {scan.scan_date ? `Last scan: ${scan.scan_date}` : 'Fetching latest data…'}
        </p>
      </div>

      {/* ── Stat Cards ── */}
      <div className="stats-grid">
        <StatCard
          label="Market Regime"
          value={loading ? '…' : regimeVal}
          sub={regime.interpretation}
          color={regimeColor}
          icon="📡"
        />
        <StatCard
          label="Stage 2 Daily"
          value={loading ? '…' : (counts.daily ?? '—')}
          sub="Stocks in Stage 2 uptrend (daily)"
          color="blue"
          icon="📈"
        />
        <StatCard
          label="Stage 2 Weekly"
          value={loading ? '…' : (counts.weekly ?? '—')}
          sub="Weinstein 10/30/40 WMA confirmed"
          color="purple"
          icon="📅"
        />
        <StatCard
          label="Stage 2 Monthly"
          value={loading ? '…' : (counts.monthly ?? '—')}
          sub="Macro trend — 12/24/48 MMA"
          color="teal"
          icon="🗓️"
        />
        <StatCard
          label="Total Scanned"
          value={loading ? '…' : (scan.total_stocks_scanned?.toLocaleString('en-IN') ?? '—')}
          sub={`NSE + BSE universe`}
          color="blue"
          icon="🔎"
        />
        <StatCard
          label="Nifty 50"
          value={loading ? '…' : (regime.nifty_close ? `₹${regime.nifty_close.toLocaleString('en-IN')}` : '—')}
          sub={regime.pct_vs_ema200 != null ? `${regime.pct_vs_ema200 > 0 ? '+' : ''}${regime.pct_vs_ema200?.toFixed(2)}% vs 200 EMA` : ''}
          color={regime.pct_vs_ema200 >= 0 ? 'green' : 'red'}
          icon="📊"
        />
      </div>

      {/* ── Market Breadth ── */}
      {Object.keys(breadth).length > 0 && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <h3 className="card-title">Market Breadth</h3>
          <div className="breadth-grid">
            {Object.entries(breadth).map(([tf, b]) => (
              <BreadthBar
                key={tf}
                label={tf}
                advancing={b.advancing ?? 0}
                declining={b.declining ?? 0}
                unchanged={b.unchanged ?? 0}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Top Performers + Opportunities ── */}
      <div className="two-col-grid">
        {/* Top Performers */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Top Performers</h3>
            <div className="tf-pill-group">
              {TF_PERF_OPTIONS.map((tf) => (
                <button
                  key={tf}
                  className={`tf-pill ${perfTf === tf ? 'active' : ''}`}
                  onClick={() => setPerfTf(tf)}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>
          <table className="data-table compact">
            <thead>
              <tr>
                <th>#</th>
                <th>Ticker</th>
                <th>Price ₹</th>
                <th>Return</th>
              </tr>
            </thead>
            <tbody>
              {loadingPerf
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}><td colSpan={4}><div className="skeleton-cell" /></td></tr>
                  ))
                : topPerf.map((s, i) => (
                    <tr key={s.ticker} className="data-row">
                      <td className="td-rank">{i + 1}</td>
                      <td className="td-symbol">{s.ticker}</td>
                      <td>₹{s.last_close?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                      <td>
                        <span className={`badge ${s.return > 0 ? 'green' : 'red'}`}>
                          {s.return > 0 ? '+' : ''}{s.return?.toFixed(2)}%
                        </span>
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>

        {/* Opportunities */}
        <div className="card">
          <h3 className="card-title">🎯 Breakout Opportunities</h3>
          <table className="data-table compact">
            <thead>
              <tr>
                <th>#</th>
                <th>Ticker</th>
                <th>Score</th>
                <th>Signals</th>
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}><td colSpan={4}><div className="skeleton-cell" /></td></tr>
                  ))
                : opps.map((o) => (
                    <tr key={o.ticker} className="data-row">
                      <td className="td-rank">{o.rank}</td>
                      <td className="td-symbol">{o.ticker}</td>
                      <td><span className="badge blue">{o.score}</span></td>
                      <td>
                        <div className="signal-pills">
                          {(o.signals || []).slice(0, 2).map((sig) => (
                            <span key={sig} className="signal-pill">{sig.replace(/_/g, ' ')}</span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
