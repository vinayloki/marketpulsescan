import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export function StockDetailPage() {
  const { symbol } = useParams<{ symbol: string }>()

  return (
    <div className="space-y-6 animate-slide-up">
      <div className="flex items-center gap-3">
        <Link
          to="/scanner"
          className="p-2 rounded-[var(--radius-md)] hover:bg-[var(--color-surface-3)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {symbol ?? 'Unknown'}
          </h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-0.5">
            Stock detail — chart, technicals, fundamentals, risk
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Chart */}
        <div className="lg:col-span-2 glass rounded-[var(--radius-lg)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4">
            Price Chart
          </h2>
          <div className="flex items-center justify-center h-72 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] text-[var(--color-text-muted)] text-sm">
            lightweight-charts integration in Sprint 4 (Story 4.4)
          </div>
        </div>

        {/* Score Panel */}
        <div className="glass rounded-[var(--radius-lg)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4">
            Scores & Recommendation
          </h2>
          <div className="flex items-center justify-center h-72 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] text-[var(--color-text-muted)] text-sm">
            Sub-scores, buy/hold/sell, per-horizon
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass rounded-[var(--radius-lg)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4">
            Technicals
          </h2>
          <div className="flex items-center justify-center h-40 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] text-[var(--color-text-muted)] text-sm">
            RSI, MACD, BB, Supertrend, ADX, Ichimoku
          </div>
        </div>
        <div className="glass rounded-[var(--radius-lg)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4">
            Fundamentals
          </h2>
          <div className="flex items-center justify-center h-40 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] text-[var(--color-text-muted)] text-sm">
            PE, PB, ROE, ROCE, EPS growth, holdings
          </div>
        </div>
      </div>

      <div className="glass rounded-[var(--radius-lg)] p-5">
        <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4">
          Risk Analysis
        </h2>
        <div className="flex items-center justify-center h-32 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] text-[var(--color-text-muted)] text-sm">
          Entry / SL / TP / RR / position sizing
        </div>
      </div>
    </div>
  )
}
