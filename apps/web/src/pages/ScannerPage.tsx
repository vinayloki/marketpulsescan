import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowDown, ArrowUp, Search } from 'lucide-react'
import { useMarket } from '../api/client'
import type { MarketStock } from '../api/client'

type SortKey = 'symbol' | 'close' | '1M' | '3M' | 'score'

export function ScannerPage() {
  const { data: market, isLoading, isError } = useMarket()
  const [query, setQuery] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('score')
  const [sortDesc, setSortDesc] = useState(true)
  const [page, setPage] = useState(1)
  const pageSize = 50

  const allRows = useMemo(() => {
    const stocks = market?.data ?? []
    const q = query.trim().toUpperCase()
    const filtered = q
      ? stocks.filter(
          (s) =>
            s.symbol.toUpperCase().includes(q) ||
            (s.name ?? '').toUpperCase().includes(q) ||
            (s.sector ?? '').toUpperCase().includes(q),
        )
      : stocks
    const val = (s: MarketStock): number | string => {
      switch (sortKey) {
        case 'symbol': return s.symbol
        case 'close': return s.close ?? 0
        case '1M': return s.returns?.['1M'] ?? -Infinity
        case '3M': return s.returns?.['3M'] ?? -Infinity
        case 'score': return s.score ?? 0
      }
    }
    return [...filtered].sort((a, b) => {
      const av = val(a)
      const bv = val(b)
      const cmp = typeof av === 'string'
        ? av.localeCompare(bv as string)
        : (av as number) - (bv as number)
      return sortDesc ? -cmp : cmp
    })
  }, [market, query, sortKey, sortDesc])

  const totalPages = Math.max(1, Math.ceil(allRows.length / pageSize))
  const currentPage = Math.min(page, totalPages)
  const rows = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return allRows.slice(start, start + pageSize)
  }, [allRows, currentPage, pageSize])

  function handleQueryChange(val: string) {
    setQuery(val)
    setPage(1)
  }

  function toggleSort(key: SortKey) {
    if (key === sortKey) setSortDesc((d) => !d)
    else {
      setSortKey(key)
      setSortDesc(key !== 'symbol')
    }
  }

  return (
    <div className="space-y-6 animate-slide-up">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Scanner</h1>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">
          {isLoading ? 'Loading scan…' : `${allRows.length} stocks in this run`}
        </p>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-text-muted)]" />
        <input
          type="text"
          value={query}
          onChange={(e) => handleQueryChange(e.target.value)}
          placeholder="Search by ticker, name, or sector..."
          className="w-full pl-10 pr-4 py-2.5 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-brand-500)] focus:ring-1 focus:ring-[var(--color-brand-500)]/30 transition-all"
        />
      </div>

      {isError && (
        <div className="glass rounded-[var(--radius-lg)] p-4 text-sm text-[var(--color-danger)]">
          Could not load dataset — check that api/v1/market.json is published.
        </div>
      )}

      {/* Table */}
      <div className="glass rounded-[var(--radius-lg)] overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--color-border)] text-left">
              <Th label="Symbol" sortKey="symbol" current={sortKey} desc={sortDesc} onSort={toggleSort} />
              <th className="px-4 py-3 font-medium text-xs uppercase tracking-wider text-[var(--color-text-muted)]">Sector</th>
              <Th label="Close" sortKey="close" current={sortKey} desc={sortDesc} onSort={toggleSort} align="right" />
              <Th label="1M %" sortKey="1M" current={sortKey} desc={sortDesc} onSort={toggleSort} align="right" />
              <Th label="3M %" sortKey="3M" current={sortKey} desc={sortDesc} onSort={toggleSort} align="right" />
              <Th label="Score" sortKey="score" current={sortKey} desc={sortDesc} onSort={toggleSort} align="right" />
              <th className="px-4 py-3 font-medium text-xs uppercase tracking-wider text-[var(--color-text-muted)]">Rec</th>
              <th className="px-4 py-3 font-medium text-xs uppercase tracking-wider text-[var(--color-text-muted)]">Signals</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {rows.map((s) => (
              <tr key={s.symbol} className="hover:bg-[var(--color-surface-2)]/50 transition-colors">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/stocks/${s.symbol}`}
                      className="font-medium hover:text-[var(--color-brand-400)] transition-colors"
                    >
                      {s.symbol}
                    </Link>
                    <div className="flex items-center gap-1 opacity-70 hover:opacity-100 transition-opacity">
                      <a
                        href={`https://in.tradingview.com/chart/?symbol=NSE:${s.symbol}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        title={`Open ${s.symbol} on TradingView`}
                        className="text-[10px] font-mono px-1 py-0.5 rounded bg-[var(--color-surface-3)] text-[var(--color-brand-400)] hover:bg-[var(--color-brand-500)]/20 transition-colors"
                      >
                        TV
                      </a>
                      <a
                        href={`https://www.screener.in/company/${s.symbol}/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        title={`Open ${s.symbol} on Screener.in`}
                        className="text-[10px] font-mono px-1 py-0.5 rounded bg-[var(--color-surface-3)] text-[var(--color-brand-400)] hover:bg-[var(--color-brand-500)]/20 transition-colors"
                      >
                        SCR
                      </a>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-[var(--color-text-muted)] text-xs">{s.sector ?? '—'}</td>
                <td className="px-4 py-3 text-right font-mono">
                  {s.close != null ? `₹${s.close.toLocaleString('en-IN')}` : '—'}
                </td>
                <PctCell value={s.returns?.['1M']} />
                <PctCell value={s.returns?.['3M']} />
                <td className="px-4 py-3 text-right font-mono font-semibold">
                  {s.score != null ? s.score.toFixed(1) : '—'}
                </td>
                <td className="px-4 py-3">
                  <RecBadge rec={s.recommendation} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {(s.signals ?? []).slice(0, 3).map((sig) => (
                      <span
                        key={sig}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-surface-2)] text-[var(--color-text-secondary)]"
                      >
                        {sig.replaceAll('_', ' ')}
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
            {!isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-[var(--color-text-muted)]">
                  No stocks match “{query}”
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Bar */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-2 text-xs text-[var(--color-text-muted)]">
          <div>
            Showing {(currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, allRows.length)} of {allRows.length} stocks
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1.5 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[var(--color-surface-3)] transition-colors"
            >
              Previous
            </button>
            <span className="font-mono">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1.5 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[var(--color-surface-3)] transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function Th({
  label,
  sortKey,
  current,
  desc,
  onSort,
  align,
}: {
  label: string
  sortKey: SortKey
  current: SortKey
  desc: boolean
  onSort: (k: SortKey) => void
  align?: 'right'
}) {
  const active = current === sortKey
  return (
    <th
      className={`px-4 py-3 font-medium text-xs uppercase tracking-wider cursor-pointer select-none transition-colors ${
        active ? 'text-[var(--color-brand-400)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
      } ${align === 'right' ? 'text-right' : 'text-left'}`}
      onClick={() => onSort(sortKey)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {active && (desc ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />)}
      </span>
    </th>
  )
}

function PctCell({ value }: { value: number | null | undefined }) {
  if (value == null) return <td className="px-4 py-3 text-right font-mono text-[var(--color-text-muted)]">—</td>
  const positive = value >= 0
  return (
    <td
      className={`px-4 py-3 text-right font-mono ${
        positive ? 'text-[var(--color-success)]' : 'text-[var(--color-danger)]'
      }`}
    >
      {positive ? '+' : ''}
      {value.toFixed(1)}%
    </td>
  )
}

function RecBadge({ rec }: { rec: string | null }) {
  if (!rec) return <span className="text-[var(--color-text-muted)]">—</span>
  const cls =
    rec === 'BUY'
      ? 'bg-[var(--color-success)]/15 text-[var(--color-success)]'
      : rec === 'SELL'
        ? 'bg-[var(--color-danger)]/15 text-[var(--color-danger)]'
        : 'bg-[var(--color-surface-2)] text-[var(--color-text-muted)]'
  return (
    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase ${cls}`}>{rec}</span>
  )
}
