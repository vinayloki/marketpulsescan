import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, TrendingUp, TrendingDown, BarChart3,
  Activity, Shield, Info, Zap, Building2, ExternalLink,
} from 'lucide-react'
import { useMarket } from '../api/client'
import type { MarketStock } from '../api/client'
import { PriceChart } from '../components/PriceChart'

// ── Sub-score colour ramp ──────────────────────────────────────────────────
function scoreColor(val: number): string {
  if (val >= 70) return 'var(--color-success)'
  if (val >= 45) return 'var(--color-warning)'
  return 'var(--color-danger)'
}

// ── Mini score bar ─────────────────────────────────────────────────────────
function ScoreBar({ label, value, max = 100 }: { label: string; value: number; max?: number }) {
  const pct = Math.min(100, (value / max) * 100)
  const color = scoreColor(value)
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-[var(--color-text-secondary)]">{label}</span>
        <span className="font-mono font-semibold" style={{ color }}>{value}</span>
      </div>
      <div className="h-1.5 rounded-full bg-[var(--color-surface-3)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  )
}

// ── Return pill ────────────────────────────────────────────────────────────
function ReturnPill({ label, value }: { label: string; value: number | null | undefined }) {
  if (value == null) return null
  const up = value >= 0
  return (
    <div className="flex flex-col items-center gap-1 p-3 rounded-[var(--radius-md)] bg-[var(--color-surface-2)]">
      <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">{label}</span>
      <span
        className="text-sm font-mono font-bold"
        style={{ color: up ? 'var(--color-success)' : 'var(--color-danger)' }}
      >
        {up ? '+' : ''}{value.toFixed(2)}%
      </span>
    </div>
  )
}

// ── Rec badge ──────────────────────────────────────────────────────────────
function RecBadge({ rec }: { rec: string | null }) {
  if (!rec) return null
  const styles: Record<string, string> = {
    BUY: 'bg-[var(--color-success)]/15 text-[var(--color-success)] border border-[var(--color-success)]/30',
    SELL: 'bg-[var(--color-danger)]/15 text-[var(--color-danger)] border border-[var(--color-danger)]/30',
    HOLD: 'bg-[var(--color-surface-3)] text-[var(--color-text-secondary)] border border-[var(--color-border)]',
  }
  return (
    <span className={`text-xs font-bold px-3 py-1 rounded-full uppercase tracking-widest ${styles[rec] ?? styles.HOLD}`}>
      {rec}
    </span>
  )
}

// ── Indicator row ──────────────────────────────────────────────────────────
function IndicatorRow({ label, value }: { label: string; value: unknown }) {
  if (value == null) return null
  const display = typeof value === 'boolean'
    ? (value ? '✓ Yes' : '✗ No')
    : typeof value === 'number'
      ? value.toFixed(2)
      : String(value)
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-[var(--color-border)] last:border-0">
      <span className="text-xs text-[var(--color-text-muted)] uppercase tracking-wide">{label.replace(/_/g, ' ')}</span>
      <span className="text-xs font-mono text-[var(--color-text-secondary)]">{display}</span>
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────
export function StockDetailPage() {
  const { symbol } = useParams<{ symbol: string }>()
  const { data: market, isLoading, isError } = useMarket()

  const stock: MarketStock | undefined = market?.data?.find(
    (s) => s.symbol === symbol
  )

  // ── Loading ──────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <BackButton />
        <div className="flex items-center justify-center h-64 text-[var(--color-text-muted)]">
          <Activity className="h-5 w-5 animate-spin mr-2" /> Loading…
        </div>
      </div>
    )
  }

  // ── Not found / error ────────────────────────────────────────────────────
  if (isError || !stock) {
    return (
      <div className="space-y-6 animate-fade-in">
        <BackButton />
        <div className="glass rounded-[var(--radius-lg)] p-8 text-center">
          <Info className="h-8 w-8 mx-auto mb-3 text-[var(--color-text-muted)]" />
          <p className="text-sm text-[var(--color-text-secondary)]">
            {isError ? 'Could not load market data.' : `Symbol "${symbol}" not found in the latest scan.`}
          </p>
        </div>
      </div>
    )
  }

  const subScores = stock.sub_scores ?? {}
  const indicators = stock.indicators ?? {}
  const returns = stock.returns ?? {}

  const returnPeriods: [string, string][] = [
    ['1D', '1 Day'], ['1W', '1 Week'], ['1M', '1 Month'],
    ['3M', '3 Mo'], ['6M', '6 Mo'], ['12M', '12 Mo'],
  ]

  const priceChange1D = returns['1D']
  const up = (priceChange1D ?? 0) >= 0

  return (
    <div className="space-y-6 animate-slide-up">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <BackButton />
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">{stock.symbol}</h1>
              <RecBadge rec={stock.recommendation} />
            </div>
            <p className="text-[var(--color-text-secondary)] text-sm mt-0.5">
              {stock.name ?? '—'}
              {stock.sector && (
                <span className="ml-2 text-[var(--color-text-muted)]">· {stock.sector}</span>
              )}
              {stock.mcap_category && (
                <span className="ml-2 text-[var(--color-text-muted)]">· {stock.mcap_category}</span>
              )}
            </p>
            <div className="flex items-center gap-2 mt-2">
              <a
                href={`https://in.tradingview.com/chart/?symbol=NSE:${stock.symbol}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] text-xs text-[var(--color-brand-400)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-brand-500)] transition-all"
              >
                TradingView <ExternalLink className="h-3 w-3" />
              </a>
              <a
                href={`https://www.screener.in/company/${stock.symbol}/`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] text-xs text-[var(--color-brand-400)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-brand-500)] transition-all"
              >
                Screener.in <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          </div>
        </div>

        {/* Live price block */}
        <div className="text-right shrink-0">
          <div className="text-3xl font-bold font-mono">
            ₹{stock.close?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          {priceChange1D != null && (
            <div
              className="text-sm font-mono mt-0.5 flex items-center justify-end gap-1"
              style={{ color: up ? 'var(--color-success)' : 'var(--color-danger)' }}
            >
              {up ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
              {up ? '+' : ''}{priceChange1D.toFixed(2)}% today
            </div>
          )}
          <div className="text-xs text-[var(--color-text-muted)] mt-1">
            Prev close: ₹{stock.prev_close?.toLocaleString('en-IN')}
          </div>
        </div>
      </div>

      {/* ── Signal Tags ────────────────────────────────────────────────── */}
      {(stock.signals ?? []).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {stock.signals.map((sig) => (
            <span
              key={sig}
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full"
              style={{
                background: 'oklch(0.55 0.19 250 / 0.15)',
                color: 'var(--color-brand-400)',
                border: '1px solid oklch(0.55 0.19 250 / 0.3)',
              }}
            >
              <Zap className="h-3 w-3" />
              {sig.replace(/_/g, ' ').toUpperCase()}
            </span>
          ))}
        </div>
      )}

      {/* ── Returns strip ──────────────────────────────────────────────── */}
      <div className="glass rounded-[var(--radius-lg)] p-4">
        <h2 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
          Performance Returns
        </h2>
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
          {returnPeriods.map(([key, label]) => (
            <ReturnPill key={key} label={label} value={returns[key]} />
          ))}
        </div>
      </div>

      {/* ── OHLC Daily Price Action Card ────────────────────────────────────── */}
      <div className="glass rounded-[var(--radius-lg)] p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
            OHLC Daily Price Action
          </h2>
          <span className="text-[11px] font-mono text-[var(--color-text-muted)]">
            Exchange: {stock.exchange}
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-surface-2)]">
            <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] block mb-1">Open</span>
            <span className="text-sm font-mono font-bold">
              {stock.open != null ? `₹${stock.open.toLocaleString('en-IN')}` : '—'}
            </span>
          </div>
          <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-surface-2)]">
            <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] block mb-1">Day High</span>
            <span className="text-sm font-mono font-bold text-[var(--color-success)]">
              {stock.high != null ? `₹${stock.high.toLocaleString('en-IN')}` : '—'}
            </span>
          </div>
          <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-surface-2)]">
            <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] block mb-1">Day Low</span>
            <span className="text-sm font-mono font-bold text-[var(--color-danger)]">
              {stock.low != null ? `₹${stock.low.toLocaleString('en-IN')}` : '—'}
            </span>
          </div>
          <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-surface-2)]">
            <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] block mb-1">Close (LTP)</span>
            <span className="text-sm font-mono font-bold text-[var(--color-brand-400)]">
              {stock.close != null ? `₹${stock.close.toLocaleString('en-IN')}` : '—'}
            </span>
          </div>
          <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-surface-2)]">
            <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] block mb-1">Prev Close</span>
            <span className="text-sm font-mono font-bold text-[var(--color-text-secondary)]">
              {stock.prev_close != null ? `₹${stock.prev_close.toLocaleString('en-IN')}` : '—'}
            </span>
          </div>
        </div>

        {/* Intraday Price Location Bar */}
        {stock.high != null && stock.low != null && stock.close != null && stock.high > stock.low && (
          <div className="mt-4 pt-3 border-t border-[var(--color-border)]">
            <div className="flex justify-between text-[11px] font-mono text-[var(--color-text-muted)] mb-1">
              <span>Low: ₹{stock.low}</span>
              <span className="text-[var(--color-text-primary)] font-semibold">Intraday Position: {(((stock.close - stock.low) / (stock.high - stock.low)) * 100).toFixed(0)}%</span>
              <span>High: ₹{stock.high}</span>
            </div>
            <div className="h-2 rounded-full bg-[var(--color-surface-3)] relative overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.max(3, Math.min(100, ((stock.close - stock.low) / (stock.high - stock.low)) * 100))}%`,
                  background: up ? 'var(--color-success)' : 'var(--color-danger)',
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* ── Score + Chart row ───────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Chart placeholder */}
        <div className="lg:col-span-2 glass rounded-[var(--radius-lg)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4 flex items-center gap-2">
            <BarChart3 className="h-4 w-4" /> Price Chart
            <span className="ml-auto text-xs text-[var(--color-text-muted)] font-normal">
              Synthetic trail from return anchors
            </span>
          </h2>
          <PriceChart stock={stock} />
        </div>

        {/* Composite score + sub-scores */}
        <div className="glass rounded-[var(--radius-lg)] p-5 space-y-4">
          <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] flex items-center gap-2">
            <Activity className="h-4 w-4" /> Composite Score
          </h2>

          {/* Big score ring substitute */}
          <div className="flex items-center justify-center py-4">
            <div className="relative flex flex-col items-center">
              <div
                className="text-5xl font-bold font-mono"
                style={{ color: stock.score != null ? scoreColor(stock.score) : 'var(--color-text-muted)' }}
              >
                {stock.score?.toFixed(0) ?? '—'}
              </div>
              <div className="text-xs text-[var(--color-text-muted)] mt-1">out of 100</div>
              <div className="mt-3"><RecBadge rec={stock.recommendation} /></div>
            </div>
          </div>

          {/* Sub-score bars */}
          {Object.keys(subScores).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(subScores).map(([key, val]) => (
                <ScoreBar key={key} label={key.charAt(0).toUpperCase() + key.slice(1)} value={val} />
              ))}
            </div>
          ) : (
            <p className="text-xs text-[var(--color-text-muted)] text-center py-4">
              Sub-scores not available in this scan run
            </p>
          )}
        </div>
      </div>

      {/* ── Technicals + Fundamentals ───────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Technicals from indicators */}
        <div className="glass rounded-[var(--radius-lg)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4 flex items-center gap-2">
            <TrendingUp className="h-4 w-4" /> Technicals
          </h2>
          {Object.keys(indicators).length > 0 ? (
            <div>
              {Object.entries(indicators).map(([k, v]) => (
                <IndicatorRow key={k} label={k} value={v} />
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-32 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] text-[var(--color-text-muted)] text-sm">
              No indicator data in this scan run
            </div>
          )}
        </div>

        {/* Fundamentals */}
        <div className="glass rounded-[var(--radius-lg)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4 flex items-center gap-2">
            <Building2 className="h-4 w-4" /> Fundamentals
          </h2>
          <div>
            <IndicatorRow label="Exchange" value={stock.exchange} />
            <IndicatorRow label="Sector" value={stock.sector} />
            <IndicatorRow label="Industry" value={(stock as unknown as Record<string, unknown>)['industry']} />
            <IndicatorRow label="Market Cap" value={stock.mcap_cr ? `₹${(stock.mcap_cr / 100).toFixed(0)}B` : null} />
            <IndicatorRow label="Cap Category" value={stock.mcap_category} />
            <IndicatorRow label="Volume (today)" value={(stock as unknown as Record<string, unknown>)['volume']} />
            <IndicatorRow label="Vol Avg 20D" value={(stock as unknown as Record<string, unknown>)['volume_avg_20d']} />
          </div>
        </div>
      </div>

      {/* ── Risk ────────────────────────────────────────────────────────── */}
      <div className="glass rounded-[var(--radius-lg)] p-5">
        <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4 flex items-center gap-2">
          <Shield className="h-4 w-4" /> Risk Analysis
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-surface-2)]">
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">52W High</div>
            <div className="text-sm font-mono font-semibold">
              ₹{(indicators['high_52w'] as number | undefined)?.toLocaleString('en-IN') ?? stock.indicators?.['high_52w'] ?? '—'}
            </div>
          </div>
          <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-surface-2)]">
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">52W Low</div>
            <div className="text-sm font-mono font-semibold">
              ₹{(indicators['low_52w'] as number | undefined)?.toLocaleString('en-IN') ?? stock.indicators?.['low_52w'] ?? '—'}
            </div>
          </div>
          <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-surface-2)]">
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">From 52W High</div>
            {stock.close != null && (indicators['high_52w'] as number) > 0 ? (() => {
              const high = indicators['high_52w'] as number
              const pct = ((stock.close - high) / high * 100).toFixed(1)
              return (
                <div
                  className="text-sm font-mono font-semibold"
                  style={{ color: Number(pct) >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}
                >
                  {Number(pct) >= 0 ? '+' : ''}{pct}%
                </div>
              )
            })() : <div className="text-sm font-mono text-[var(--color-text-muted)]">—</div>}
          </div>
          <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-surface-2)]">
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">From 52W Low</div>
            {stock.close != null && (indicators['low_52w'] as number) > 0 ? (() => {
              const low = indicators['low_52w'] as number
              const pct = ((stock.close - low) / low * 100).toFixed(1)
              return (
                <div
                  className="text-sm font-mono font-semibold"
                  style={{ color: 'var(--color-success)' }}
                >
                  +{pct}%
                </div>
              )
            })() : <div className="text-sm font-mono text-[var(--color-text-muted)]">—</div>}
          </div>
        </div>
        <p className="text-xs text-[var(--color-text-muted)] mt-4">
          Position sizing, SL/TP, and R:R calculator coming in Sprint 4 (Risk module integration).
        </p>
      </div>

    </div>
  )
}

function BackButton() {
  return (
    <Link
      to="/scanner"
      className="p-2 rounded-[var(--radius-md)] hover:bg-[var(--color-surface-3)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors flex-shrink-0"
    >
      <ArrowLeft className="h-4 w-4" />
    </Link>
  )
}
