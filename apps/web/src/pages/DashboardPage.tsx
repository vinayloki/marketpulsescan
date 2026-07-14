import { TrendingUp, TrendingDown, BarChart3, Zap } from 'lucide-react'

export function DashboardPage() {
  return (
    <div className="space-y-6 animate-slide-up">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Market Overview</h1>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">
          Indian equity market pulse — updated nightly after NSE close
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Market Regime"
          value="—"
          subtitle="Awaiting pipeline data"
          icon={<Zap className="h-5 w-5" />}
          color="brand"
        />
        <StatCard
          label="Stocks Scanned"
          value="—"
          subtitle="NSE + BSE universe"
          icon={<BarChart3 className="h-5 w-5" />}
          color="brand"
        />
        <StatCard
          label="Bullish Signals"
          value="—"
          subtitle="Breakout + momentum"
          icon={<TrendingUp className="h-5 w-5" />}
          color="success"
        />
        <StatCard
          label="Bearish Signals"
          value="—"
          subtitle="Breakdown + weakness"
          icon={<TrendingDown className="h-5 w-5" />}
          color="danger"
        />
      </div>

      {/* Placeholder Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <PlaceholderPanel title="Top Movers" span={1} />
        <PlaceholderPanel title="AI Picks Preview" span={1} />
        <PlaceholderPanel title="Sector Heatmap" span={1} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <PlaceholderPanel title="Market Breadth" span={1} />
        <PlaceholderPanel title="News & Regime" span={1} />
      </div>
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

function PlaceholderPanel({ title, span }: { title: string; span: number }) {
  return (
    <div
      className={`glass rounded-[var(--radius-lg)] p-5 ${
        span === 2 ? 'lg:col-span-2' : ''
      }`}
    >
      <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4">
        {title}
      </h2>
      <div className="flex items-center justify-center h-40 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] text-[var(--color-text-muted)] text-sm">
        Connected to pipeline in Sprint 4
      </div>
    </div>
  )
}
