import { TrendingUp, TrendingDown, BarChart3, Zap, PieChart } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useManifest, useMarket } from '../api/client'
import type { MarketStock } from '../api/client'

// ── Derived regime from BUY % ─────────────────────────────────────────────
function deriveRegime(stocks: MarketStock[]): { label: string; color: string; desc: string } {
  if (stocks.length === 0) return { label: '—', color: 'var(--color-text-muted)', desc: 'No data' }
  const buyPct = stocks.filter((s) => s.recommendation === 'BUY').length / stocks.length
  const sellPct = stocks.filter((s) => s.recommendation === 'SELL').length / stocks.length
  if (buyPct >= 0.55) return { label: 'Bull', color: 'var(--color-success)', desc: `${Math.round(buyPct * 100)}% BUY signals` }
  if (sellPct >= 0.45) return { label: 'Bear', color: 'var(--color-danger)', desc: `${Math.round(sellPct * 100)}% SELL signals` }
  return { label: 'Sideways', color: 'var(--color-warning)', desc: 'Mixed momentum' }
}

export function DashboardPage() {
  const { data: manifest } = useManifest()
  const { data: market, isLoading, isError } = useMarket()

  const stocks = market?.data ?? []
  const buys = stocks.filter((s) => s.recommendation === 'BUY')
  const sells = stocks.filter((s) => s.recommendation === 'SELL')
  const holds = stocks.filter((s) => s.recommendation === 'HOLD')
  const asOf = manifest?.files?.[0]?.as_of
  const regime = deriveRegime(stocks)

  // Market breadth
  const gainers = stocks.filter((s) => (s.returns?.['1D'] ?? 0) > 0)
  const losers = stocks.filter((s) => (s.returns?.['1D'] ?? 0) < 0)
  const flat = stocks.filter((s) => (s.returns?.['1D'] ?? 0) === 0)

  // Sector leaders
  const sectorMap: Record<string, { scores: number[]; stocks: MarketStock[] }> = {}
  for (const s of stocks) {
    const sec = s.sector ?? 'Unknown'
    if (!sectorMap[sec]) sectorMap[sec] = { scores: [], stocks: [] }
    if (s.score != null) sectorMap[sec].scores.push(s.score)
    sectorMap[sec].stocks.push(s)
  }
  const sectorRanked = Object.entries(sectorMap)
    .map(([name, { scores, stocks: ss }]) => ({
      name,
      avg: scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0,
      count: ss.length,
      buys: ss.filter((s) => s.recommendation === 'BUY').length,
    }))
    .sort((a, b) => b.avg - a.avg)

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Market Overview</h1>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">
          Indian equity market pulse — updated nightly after NSE close
          {asOf && (
            <span className="ml-2 text-[var(--color-text-muted)]">
              · data as of {asOf} (run {manifest?.run_id})
            </span>
          )}
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard
          label="Market Regime"
          value={regime.label}
          subtitle={regime.desc}
          icon={<Zap className="h-5 w-5" />}
          color="brand"
          valueColor={regime.color}
        />
        <StatCard
          label="Stocks Scanned"
          value={isLoading ? '…' : String(stocks.length)}
          subtitle="This scan run"
          icon={<BarChart3 className="h-5 w-5" />}
          color="brand"
        />
        <StatCard
          label="Buy Signals"
          value={isLoading ? '…' : String(buys.length)}
          subtitle={`${holds.length} HOLD · ${sells.length} SELL`}
          icon={<TrendingUp className="h-5 w-5" />}
          color="success"
        />
        <StatCard
          label="Today Gainers"
          value={isLoading ? '…' : String(gainers.length)}
          subtitle={`${losers.length} losers · ${flat.length} flat`}
          icon={<TrendingDown className="h-5 w-5" />}
          color={gainers.length >= losers.length ? 'success' : 'danger'}
        />
      </div>

      {isError && (
        <div className="glass rounded-[var(--radius-lg)] p-4 text-sm text-[var(--color-danger)]">
          Could not load dataset — check that api/v1/market.json is published.
        </div>
      )}

      {/* Market Breadth */}
      {stocks.length > 0 && (
        <div className="glass rounded-[var(--radius-lg)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4">Market Breadth (1-Day)</h2>
          <div className="flex items-center gap-1 h-6 rounded-full overflow-hidden">
            {gainers.length > 0 && (
              <div
                className="h-full rounded-l-full transition-all"
                style={{ width: `${(gainers.length / stocks.length) * 100}%`, background: 'var(--color-success)', opacity: 0.85 }}
                title={`${gainers.length} gainers`}
              />
            )}
            {flat.length > 0 && (
              <div
                className="h-full"
                style={{ width: `${(flat.length / stocks.length) * 100}%`, background: 'var(--color-surface-4)' }}
                title={`${flat.length} flat`}
              />
            )}
            {losers.length > 0 && (
              <div
                className="h-full rounded-r-full"
                style={{ width: `${(losers.length / stocks.length) * 100}%`, background: 'var(--color-danger)', opacity: 0.85 }}
                title={`${losers.length} losers`}
              />
            )}
          </div>
          <div className="flex justify-between mt-2 text-xs text-[var(--color-text-muted)]">
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-sm" style={{ background: 'var(--color-success)' }} />
              {gainers.length} gainers
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-sm bg-[var(--color-surface-4)]" />
              {flat.length} flat
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-sm" style={{ background: 'var(--color-danger)' }} />
              {losers.length} losers
            </span>
          </div>
        </div>
      )}

      {/* Data Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <MoversPanel title="Top Scores" stocks={topBy(stocks, (s) => s.score ?? 0)} field="score" />
        <MoversPanel
          title="Top Movers (1M)"
          stocks={topBy(stocks, (s) => s.returns?.['1M'] ?? -Infinity)}
          field="1M"
        />
        {/* Sector Leaders */}
        <div className="glass rounded-[var(--radius-lg)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4 flex items-center gap-2">
            <PieChart className="h-4 w-4" /> Sector Leaders
          </h2>
          {sectorRanked.length === 0 ? (
            <div className="flex items-center justify-center h-40 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] text-[var(--color-text-muted)] text-sm">
              Awaiting pipeline data
            </div>
          ) : (
            <ul className="space-y-3">
              {sectorRanked.slice(0, 5).map((sec, i) => (
                <li key={sec.name}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-medium truncate max-w-[140px]" title={sec.name}>
                      {i + 1}. {sec.name}
                    </span>
                    <span className="font-mono text-[var(--color-text-secondary)]">
                      {sec.avg.toFixed(0)} · {sec.buys}/{sec.count} BUY
                    </span>
                  </div>
                  <div className="h-1 rounded-full bg-[var(--color-surface-3)] overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${sec.avg}%`,
                        background: sec.avg >= 65 ? 'var(--color-success)' : sec.avg >= 45 ? 'var(--color-brand-400)' : 'var(--color-warning)',
                      }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

function topBy(stocks: MarketStock[], key: (s: MarketStock) => number): MarketStock[] {
  return [...stocks].sort((a, b) => key(b) - key(a)).slice(0, 5)
}

function MoversPanel({
  title,
  stocks,
  field,
}: {
  title: string
  stocks: MarketStock[]
  field: 'score' | '1M'
}) {
  return (
    <div className="glass rounded-[var(--radius-lg)] p-5">
      <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4">{title}</h2>
      {stocks.length === 0 ? (
        <div className="flex items-center justify-center h-40 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] text-[var(--color-text-muted)] text-sm">
          Awaiting pipeline data
        </div>
      ) : (
        <ul className="divide-y divide-[var(--color-border)]">
          {stocks.map((s) => {
            const value = field === 'score' ? (s.score ?? 0) : (s.returns?.['1M'] ?? 0)
            const positive = field === 'score' ? s.recommendation === 'BUY' : value >= 0
            return (
              <li key={s.symbol} className="flex items-center justify-between py-2.5">
                <div>
                  <Link
                    to={`/stocks/${s.symbol}`}
                    className="font-medium text-sm hover:text-[var(--color-brand-400)] transition-colors"
                  >
                    {s.symbol}
                  </Link>
                  <span className="ml-2 text-xs text-[var(--color-text-muted)]">
                    ₹{s.close?.toLocaleString('en-IN')}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  {s.recommendation && (
                    <span
                      className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase ${
                        s.recommendation === 'BUY'
                          ? 'bg-[var(--color-success)]/15 text-[var(--color-success)]'
                          : s.recommendation === 'SELL'
                            ? 'bg-[var(--color-danger)]/15 text-[var(--color-danger)]'
                            : 'bg-[var(--color-surface-2)] text-[var(--color-text-muted)]'
                      }`}
                    >
                      {s.recommendation}
                    </span>
                  )}
                  <span
                    className={`text-sm font-mono ${
                      positive ? 'text-[var(--color-success)]' : 'text-[var(--color-text-secondary)]'
                    }`}
                  >
                    {field === 'score' ? (value as number).toFixed(1) : `${value >= 0 ? '+' : ''}${(value as number).toFixed(1)}%`}
                  </span>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function StatCard({
  label,
  value,
  subtitle,
  icon,
  color,
  valueColor,
}: {
  label: string
  value: string
  subtitle: string
  icon: React.ReactNode
  color: 'brand' | 'success' | 'danger'
  valueColor?: string
}) {
  const colorMap = {
    brand: 'text-[var(--color-brand-400)]',
    success: 'text-[var(--color-success)]',
    danger: 'text-[var(--color-danger)]',
  }

  return (
    <div className="glass rounded-[var(--radius-lg)] p-4 glass-hover transition-all duration-200 cursor-default">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
          {label}
        </span>
        <span className={colorMap[color]}>{icon}</span>
      </div>
      <div
        className="text-2xl font-bold tracking-tight"
        style={valueColor ? { color: valueColor } : undefined}
      >
        {value}
      </div>
      <div className="text-xs text-[var(--color-text-muted)] mt-1">{subtitle}</div>
    </div>
  )
}
