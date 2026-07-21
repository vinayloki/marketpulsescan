import { useMemo, useState } from 'react'
import { Sparkles, TrendingUp, TrendingDown, Zap, Filter } from 'lucide-react'
import { useMarket } from '../api/client'
import type { MarketStock } from '../api/client'
import { StockBadge } from '../components/StockBadge'

// ── Score bar ─────────────────────────────────────────────────────────────
function MiniScoreBar({ value }: { value: number }) {
  const color = value >= 70 ? 'var(--color-success)' : value >= 45 ? 'var(--color-warning)' : 'var(--color-danger)'
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-[var(--color-surface-3)] overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${value}%`, background: color }} />
      </div>
      <span className="text-xs font-mono" style={{ color }}>{value.toFixed(0)}</span>
    </div>
  )
}

function ReturnChip({ value }: { value: number | null | undefined }) {
  if (value == null) return <span className="text-xs text-[var(--color-text-muted)]">—</span>
  const up = value >= 0
  return (
    <span
      className="text-xs font-mono"
      style={{ color: up ? 'var(--color-success)' : 'var(--color-danger)' }}
    >
      {up ? '+' : ''}{value.toFixed(1)}%
    </span>
  )
}

function RecBadge({ rec }: { rec: string | null }) {
  if (!rec) return null
  const styles: Record<string, string> = {
    BUY: 'bg-[var(--color-success)]/15 text-[var(--color-success)]',
    SELL: 'bg-[var(--color-danger)]/15 text-[var(--color-danger)]',
    HOLD: 'bg-[var(--color-surface-3)] text-[var(--color-text-muted)]',
  }
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${styles[rec] ?? styles.HOLD}`}>
      {rec}
    </span>
  )
}

export function AiPicksPage() {
  const { data: market, isLoading, isError } = useMarket()
  const [recFilter, setRecFilter] = useState<'ALL' | 'BUY' | 'HOLD' | 'SELL'>('BUY')
  const [capFilter, setCapFilter] = useState<string>('ALL')
  const [sectorFilter, setSectorFilter] = useState<string>('ALL')

  const allStocks = market?.data ?? []

  // Build sector list
  const sectors = useMemo(() => {
    const set = new Set(allStocks.map((s) => s.sector ?? 'Unknown'))
    return ['ALL', ...Array.from(set).sort()]
  }, [allStocks])

  // Build cap categories
  const caps = useMemo(() => {
    const set = new Set(allStocks.map((s) => s.mcap_category ?? 'Unknown'))
    return ['ALL', ...Array.from(set).sort()]
  }, [allStocks])

  // Filter + sort
  const picks = useMemo(() => {
    return allStocks
      .filter((s) => {
        if (recFilter !== 'ALL' && s.recommendation !== recFilter) return false
        if (capFilter !== 'ALL' && (s.mcap_category ?? 'Unknown') !== capFilter) return false
        if (sectorFilter !== 'ALL' && (s.sector ?? 'Unknown') !== sectorFilter) return false
        return true
      })
      .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
  }, [allStocks, recFilter, capFilter, sectorFilter])

  const FilterChip = ({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) => (
    <button
      onClick={onClick}
      className={`px-3 py-1 rounded-full text-xs font-medium transition-all duration-150 ${
        active
          ? 'bg-[var(--color-brand-500)]/20 text-[var(--color-brand-300)] border border-[var(--color-brand-500)]/40'
          : 'bg-[var(--color-surface-2)] text-[var(--color-text-muted)] border border-[var(--color-border)] hover:border-[var(--color-border-hover)] hover:text-[var(--color-text-secondary)]'
      }`}
    >
      {label}
    </button>
  )

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-[var(--color-brand-400)]" />
          <h1 className="text-2xl font-bold tracking-tight">AI Picks</h1>
        </div>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">
          Top-ranked opportunities — composite score, multi-factor model
        </p>
      </div>

      {/* Filter bar */}
      <div className="glass rounded-[var(--radius-lg)] p-4 space-y-3">
        <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
          <Filter className="h-3.5 w-3.5" />
          <span className="uppercase tracking-wider font-medium">Filters</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-[var(--color-text-muted)] self-center">Signal:</span>
          {(['ALL', 'BUY', 'HOLD', 'SELL'] as const).map((r) => (
            <FilterChip key={r} label={r} active={recFilter === r} onClick={() => setRecFilter(r)} />
          ))}
        </div>
        {caps.length > 2 && (
          <div className="flex flex-wrap gap-2">
            <span className="text-xs text-[var(--color-text-muted)] self-center">Cap:</span>
            {caps.map((c) => (
              <FilterChip key={c} label={c} active={capFilter === c} onClick={() => setCapFilter(c)} />
            ))}
          </div>
        )}
        {sectors.length > 2 && (
          <div className="flex flex-wrap gap-2">
            <span className="text-xs text-[var(--color-text-muted)] self-center">Sector:</span>
            {sectors.map((s) => (
              <FilterChip key={s} label={s === 'ALL' ? 'All Sectors' : s} active={sectorFilter === s} onClick={() => setSectorFilter(s)} />
            ))}
          </div>
        )}
      </div>

      {isError && (
        <div className="glass rounded-[var(--radius-lg)] p-4 text-sm text-[var(--color-danger)]">
          Could not load dataset.
        </div>
      )}

      {/* Results count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-[var(--color-text-muted)]">
          {isLoading ? '…' : `${picks.length} stock${picks.length !== 1 ? 's' : ''} match`}
        </p>
      </div>

      {/* Picks table */}
      <div className="glass rounded-[var(--radius-lg)] overflow-hidden">
        {picks.length === 0 && !isLoading ? (
          <div className="flex flex-col items-center justify-center h-48 text-[var(--color-text-muted)] text-sm gap-2">
            <Sparkles className="h-8 w-8 opacity-30" />
            No stocks match the selected filters
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left">
                  <th className="px-4 py-3 font-medium text-xs uppercase tracking-wider text-[var(--color-text-muted)] w-8">#</th>
                  <th className="px-4 py-3 font-medium text-xs uppercase tracking-wider text-[var(--color-text-muted)]">Symbol</th>
                  <th className="px-4 py-3 font-medium text-xs uppercase tracking-wider text-[var(--color-text-muted)] hidden sm:table-cell">Sector</th>
                  <th className="px-4 py-3 font-medium text-xs uppercase tracking-wider text-[var(--color-text-muted)] text-right">Close</th>
                  <th className="px-4 py-3 font-medium text-xs uppercase tracking-wider text-[var(--color-text-muted)] text-right">1M</th>
                  <th className="px-4 py-3 font-medium text-xs uppercase tracking-wider text-[var(--color-text-muted)] text-right">3M</th>
                  <th className="px-4 py-3 font-medium text-xs uppercase tracking-wider text-[var(--color-text-muted)]">Score</th>
                  <th className="px-4 py-3 font-medium text-xs uppercase tracking-wider text-[var(--color-text-muted)]">Rec</th>
                  <th className="px-4 py-3 font-medium text-xs uppercase tracking-wider text-[var(--color-text-muted)] hidden md:table-cell">Signals</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {picks.map((s: MarketStock, i) => (
                  <tr key={s.symbol} className="hover:bg-[var(--color-surface-2)]/50 transition-colors group">
                    <td className="px-4 py-3 text-[var(--color-text-muted)] text-xs font-mono">{i + 1}</td>
                    <td className="px-4 py-3">
                      <StockBadge stock={s} showNames />
                    </td>
                    <td className="px-4 py-3 text-xs text-[var(--color-text-muted)] hidden sm:table-cell">{s.sector ?? '—'}</td>
                    <td className="px-4 py-3 text-right font-mono text-sm">
                      {s.close != null ? `₹${s.close.toLocaleString('en-IN')}` : '—'}
                    </td>
                    <td className="px-4 py-3 text-right"><ReturnChip value={s.returns?.['1M']} /></td>
                    <td className="px-4 py-3 text-right"><ReturnChip value={s.returns?.['3M']} /></td>
                    <td className="px-4 py-3">
                      {s.score != null ? <MiniScoreBar value={s.score} /> : <span className="text-[var(--color-text-muted)]">—</span>}
                    </td>
                    <td className="px-4 py-3"><RecBadge rec={s.recommendation} /></td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {(s.signals ?? []).slice(0, 3).map((sig) => (
                          <span
                            key={sig}
                            className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded"
                            style={{
                              background: 'oklch(0.55 0.19 250 / 0.1)',
                              color: 'var(--color-brand-400)',
                            }}
                          >
                            <Zap className="h-2.5 w-2.5" />
                            {sig.replace(/_/g, ' ')}
                          </span>
                        ))}
                        {(s.signals ?? []).length > 3 && (
                          <span className="text-[10px] text-[var(--color-text-muted)]">
                            +{(s.signals ?? []).length - 3}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Stats footer */}
      {picks.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          {[
            {
              label: 'Avg Score',
              value: (picks.reduce((a, s) => a + (s.score ?? 0), 0) / picks.length).toFixed(1),
              icon: <Sparkles className="h-4 w-4" />,
            },
            {
              label: 'Avg 1M Return',
              value: (() => {
                const vals = picks.map(s => s.returns?.['1M']).filter(v => v != null) as number[]
                if (!vals.length) return '—'
                const avg = vals.reduce((a, b) => a + b, 0) / vals.length
                return `${avg >= 0 ? '+' : ''}${avg.toFixed(1)}%`
              })(),
              icon: <TrendingUp className="h-4 w-4" />,
            },
            {
              label: 'Avg 3M Return',
              value: (() => {
                const vals = picks.map(s => s.returns?.['3M']).filter(v => v != null) as number[]
                if (!vals.length) return '—'
                const avg = vals.reduce((a, b) => a + b, 0) / vals.length
                return `${avg >= 0 ? '+' : ''}${avg.toFixed(1)}%`
              })(),
              icon: <TrendingDown className="h-4 w-4" />,
            },
          ].map(({ label, value, icon }) => (
            <div key={label} className="glass rounded-[var(--radius-lg)] p-4 flex items-center gap-3">
              <span className="text-[var(--color-brand-400)]">{icon}</span>
              <div>
                <div className="text-xs text-[var(--color-text-muted)]">{label}</div>
                <div className="text-lg font-bold font-mono">{value}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
