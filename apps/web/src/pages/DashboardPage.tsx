import { TrendingUp, TrendingDown, BarChart3, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useManifest, useMarket } from '../api/client'
import type { MarketStock } from '../api/client'

export function DashboardPage() {
  const { data: manifest } = useManifest()
  const { data: market, isLoading, isError } = useMarket()

  const stocks = market?.data ?? []
  const buys = stocks.filter((s) => s.recommendation === 'BUY')
  const sells = stocks.filter((s) => s.recommendation === 'SELL')
  const asOf = manifest?.files?.[0]?.as_of

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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Market Regime"
          value="—"
          subtitle="Regime module lands in Sprint 3"
          icon={<Zap className="h-5 w-5" />}
          color="brand"
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
          subtitle="Composite score ≥ BUY threshold"
          icon={<TrendingUp className="h-5 w-5" />}
          color="success"
        />
        <StatCard
          label="Sell Signals"
          value={isLoading ? '…' : String(sells.length)}
          subtitle="Breakdown + weakness"
          icon={<TrendingDown className="h-5 w-5" />}
          color="danger"
        />
      </div>

      {isError && (
        <div className="glass rounded-[var(--radius-lg)] p-4 text-sm text-[var(--color-danger)]">
          Could not load dataset — check that api/v1/market.json is published.
        </div>
      )}

      {/* Data Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <MoversPanel title="Top Scores" stocks={topBy(stocks, (s) => s.score ?? 0)} field="score" />
        <MoversPanel
          title="Top Movers (1M)"
          stocks={topBy(stocks, (s) => s.returns?.['1M'] ?? -Infinity)}
          field="1M"
        />
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
            const value =
              field === 'score' ? (s.score ?? 0) : (s.returns?.['1M'] ?? 0)
            const positive = field === 'score' ? (s.recommendation === 'BUY') : value >= 0
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
                    {field === 'score' ? value.toFixed(1) : `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`}
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
}: {
  label: string
  value: string
  subtitle: string
  icon: React.ReactNode
  color: 'brand' | 'success' | 'danger'
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
      <div className="text-2xl font-bold tracking-tight">{value}</div>
      <div className="text-xs text-[var(--color-text-muted)] mt-1">{subtitle}</div>
    </div>
  )
}
