import { useMemo, useState } from 'react'
import { ArrowDown, ArrowUp, Search, SlidersHorizontal, X } from 'lucide-react'
import { useMarket } from '../api/client'
import type { MarketStock } from '../api/client'
import { StockBadge } from '../components/StockBadge'

type SortKey =
  | 'symbol' | 'sector' | 'close'
  | '1D' | '1W' | '1M' | '3M' | '6M' | '12M'
  | 'rsi' | 'adx' | 'score' | 'rec'

type Operator = '>' | '>=' | '<' | '<=' | '='

interface NumFilter { op: Operator; val: string }

const DEFAULT_NUM: NumFilter = { op: '>', val: '' }

function applyNumFilter(value: number | undefined | null, f: NumFilter): boolean {
  if (f.val === '') return true
  if (value == null) return false
  const threshold = parseFloat(f.val)
  if (isNaN(threshold)) return true
  switch (f.op) {
    case '>':  return value > threshold
    case '>=': return value >= threshold
    case '<':  return value < threshold
    case '<=': return value <= threshold
    case '=':  return Math.abs(value - threshold) < 0.05
  }
}

export function ScannerPage() {
  const { data: market, isLoading, isError } = useMarket()

  // ── Search & basic filters ──────────────────────────────────────────────
  const [query, setQuery]             = useState('')
  const [sectorFilter, setSectorFilter] = useState('ALL')
  const [recFilter, setRecFilter]     = useState('ALL')
  const [only52wHigh, setOnly52wHigh] = useState(false)

  // ── Numeric filters ─────────────────────────────────────────────────────
  const [rsiFilter, setRsiFilter]   = useState<NumFilter>(DEFAULT_NUM)
  const [adxFilter, setAdxFilter]   = useState<NumFilter>(DEFAULT_NUM)
  const [closeMin, setCloseMin]     = useState('')
  const [closeMax, setCloseMax]     = useState('')

  // ── Sort ────────────────────────────────────────────────────────────────
  const [sortKey, setSortKey] = useState<SortKey>('score')
  const [sortDesc, setSortDesc] = useState(true)

  // ── Pagination ───────────────────────────────────────────────────────────
  const [page, setPage] = useState(1)
  const pageSize = 50

  const stocks = market?.data ?? []

  // Build sector list
  const sectors = useMemo(() => {
    const set = new Set(stocks.map((s) => s.sector ?? 'Unknown'))
    return ['ALL', ...Array.from(set).sort()]
  }, [stocks])

  // Build rec list
  const recs = ['ALL', 'BUY', 'HOLD', 'SELL']

  // 52W-High detection helper
  function is52wHigh(s: MarketStock): boolean {
    const high52 = (s.indicators?.high_52w as number | undefined) ?? (s.high_52w as number | undefined)
    return (
      (s.close != null && high52 != null && s.close >= high52 * 0.985) ||
      (s.signals ?? []).includes('52W_HIGH') ||
      (s.signals ?? []).includes('BREAKOUT_52W_HIGH')
    )
  }

  // ── Filter + sort logic ──────────────────────────────────────────────────
  const allRows = useMemo(() => {
    const q = query.trim().toUpperCase()

    const filtered = stocks.filter((s) => {
      // text search
      if (q && !s.symbol.toUpperCase().includes(q) && !(s.name ?? '').toUpperCase().includes(q) && !(s.sector ?? '').toUpperCase().includes(q)) return false
      // sector
      if (sectorFilter !== 'ALL' && (s.sector ?? 'Unknown') !== sectorFilter) return false
      // recommendation
      if (recFilter !== 'ALL' && s.recommendation !== recFilter) return false
      // 52W High
      if (only52wHigh && !is52wHigh(s)) return false
      // RSI filter
      const rsiVal = s.indicators?.rsi_14 as number | undefined
      if (!applyNumFilter(rsiVal, rsiFilter)) return false
      // ADX filter
      const adxVal = s.indicators?.adx_14 as number | undefined
      if (!applyNumFilter(adxVal, adxFilter)) return false
      // Close price range
      if (closeMin !== '' && (s.close ?? 0) < parseFloat(closeMin)) return false
      if (closeMax !== '' && (s.close ?? 0) > parseFloat(closeMax)) return false
      return true
    })

    const val = (s: MarketStock): number | string => {
      switch (sortKey) {
        case 'symbol':  return s.symbol
        case 'sector':  return s.sector ?? ''
        case 'close':   return s.close ?? 0
        case '1D':      return s.returns?.['1D'] ?? -Infinity
        case '1W':      return s.returns?.['1W'] ?? -Infinity
        case '1M':      return s.returns?.['1M'] ?? -Infinity
        case '3M':      return s.returns?.['3M'] ?? -Infinity
        case '6M':      return s.returns?.['6M'] ?? -Infinity
        case '12M':     return s.returns?.['12M'] ?? -Infinity
        case 'rsi':     return (s.indicators?.rsi_14 as number | undefined) ?? -Infinity
        case 'adx':     return (s.indicators?.adx_14 as number | undefined) ?? -Infinity
        case 'score':   return s.score ?? 0
        case 'rec':     return s.recommendation ?? ''
      }
    }

    return [...filtered].sort((a, b) => {
      const av = val(a)
      const bv = val(b)
      const cmp = typeof av === 'string' ? av.localeCompare(bv as string) : (av as number) - (bv as number)
      return sortDesc ? -cmp : cmp
    })
  }, [stocks, query, sectorFilter, recFilter, only52wHigh, rsiFilter, adxFilter, closeMin, closeMax, sortKey, sortDesc])

  const totalPages = Math.max(1, Math.ceil(allRows.length / pageSize))
  const currentPage = Math.min(page, totalPages)
  const rows = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return allRows.slice(start, start + pageSize)
  }, [allRows, currentPage])

  function handleQuery(val: string) { setQuery(val); setPage(1) }
  function toggleSort(key: SortKey) {
    if (key === sortKey) setSortDesc((d) => !d)
    else { setSortKey(key); setSortDesc(key !== 'symbol' && key !== 'sector') }
    setPage(1)
  }
  function resetFilters() {
    setQuery(''); setSectorFilter('ALL'); setRecFilter('ALL'); setOnly52wHigh(false)
    setRsiFilter(DEFAULT_NUM); setAdxFilter(DEFAULT_NUM); setCloseMin(''); setCloseMax('')
    setPage(1)
  }

  const hasActiveFilters = query || sectorFilter !== 'ALL' || recFilter !== 'ALL' || only52wHigh ||
    rsiFilter.val !== '' || adxFilter.val !== '' || closeMin !== '' || closeMax !== ''

  return (
    <div className="space-y-5 animate-slide-up">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Stock Scanner</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">
            {isLoading ? 'Loading…' : `${allRows.length.toLocaleString()} stocks matched`}
          </p>
        </div>
        {hasActiveFilters && (
          <button
            onClick={resetFilters}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-[var(--radius-md)] bg-[var(--color-danger)]/10 text-[var(--color-danger)] hover:bg-[var(--color-danger)]/20 transition-colors border border-[var(--color-danger)]/20"
          >
            <X className="h-3 w-3" /> Clear Filters
          </button>
        )}
      </div>

      {/* ── Filter Panel ─────────────────────────────────────────────────── */}
      <div className="glass rounded-[var(--radius-lg)] p-4 space-y-4">
        <div className="flex items-center gap-2 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
          <SlidersHorizontal className="h-3.5 w-3.5" />
          Filters
        </div>

        {/* Row 1: Search + Sector + Rec + 52W High */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Search */}
          <div className="relative col-span-1 sm:col-span-2 lg:col-span-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-text-muted)]" />
            <input
              type="text"
              value={query}
              onChange={(e) => handleQuery(e.target.value)}
              placeholder="Ticker, name, sector…"
              className="w-full pl-9 pr-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] text-sm placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-brand-500)] focus:ring-1 focus:ring-[var(--color-brand-500)]/30 transition-all"
            />
          </div>

          {/* Sector */}
          <select
            value={sectorFilter}
            onChange={(e) => { setSectorFilter(e.target.value); setPage(1) }}
            className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] text-sm focus:outline-none focus:border-[var(--color-brand-500)] transition-all"
          >
            {sectors.map((s) => <option key={s} value={s}>{s === 'ALL' ? 'All Sectors' : s}</option>)}
          </select>

          {/* Rec */}
          <select
            value={recFilter}
            onChange={(e) => { setRecFilter(e.target.value); setPage(1) }}
            className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] text-sm focus:outline-none focus:border-[var(--color-brand-500)] transition-all"
          >
            {recs.map((r) => <option key={r} value={r}>{r === 'ALL' ? 'All Recommendations' : r}</option>)}
          </select>

          {/* 52W High toggle */}
          <button
            onClick={() => { setOnly52wHigh((v) => !v); setPage(1) }}
            className={`flex items-center justify-center gap-2 px-3 py-2 rounded-[var(--radius-md)] border text-sm font-medium transition-colors ${
              only52wHigh
                ? 'bg-[var(--color-brand-500)]/20 border-[var(--color-brand-500)] text-[var(--color-brand-400)]'
                : 'bg-[var(--color-surface-2)] border-[var(--color-border)] text-[var(--color-text-muted)] hover:border-[var(--color-brand-500)]/50'
            }`}
          >
            <span>🚀</span> 52W High Only
          </button>
        </div>

        {/* Row 2: Numeric filters */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* RSI filter */}
          <NumFilterInput label="RSI (14)" filter={rsiFilter} onChange={(f) => { setRsiFilter(f); setPage(1) }} min={0} max={100} />

          {/* ADX filter */}
          <NumFilterInput label="ADX (14)" filter={adxFilter} onChange={(f) => { setAdxFilter(f); setPage(1) }} min={0} max={100} />

          {/* Close min */}
          <div>
            <label className="block text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-1">Price Min (₹)</label>
            <input
              type="number"
              value={closeMin}
              onChange={(e) => { setCloseMin(e.target.value); setPage(1) }}
              placeholder="e.g. 100"
              className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] text-sm font-mono focus:outline-none focus:border-[var(--color-brand-500)] focus:ring-1 focus:ring-[var(--color-brand-500)]/30 transition-all"
            />
          </div>

          {/* Close max */}
          <div>
            <label className="block text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-1">Price Max (₹)</label>
            <input
              type="number"
              value={closeMax}
              onChange={(e) => { setCloseMax(e.target.value); setPage(1) }}
              placeholder="e.g. 5000"
              className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] text-sm font-mono focus:outline-none focus:border-[var(--color-brand-500)] focus:ring-1 focus:ring-[var(--color-brand-500)]/30 transition-all"
            />
          </div>
        </div>
      </div>

      {isError && (
        <div className="glass rounded-[var(--radius-lg)] p-4 text-sm text-[var(--color-danger)]">
          Could not load dataset — check that api/v1/market.json is published.
        </div>
      )}

      {/* ── Table ────────────────────────────────────────────────────────── */}
      <div className="glass rounded-[var(--radius-lg)] overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--color-border)] text-left bg-[var(--color-surface-2)]/30">
              <Th label="Symbol"  sk="symbol" cur={sortKey} desc={sortDesc} onSort={toggleSort} />
              <Th label="Sector"  sk="sector" cur={sortKey} desc={sortDesc} onSort={toggleSort} />
              <Th label="Close"   sk="close"  cur={sortKey} desc={sortDesc} onSort={toggleSort} align="right" />
              <Th label="1D %"    sk="1D"     cur={sortKey} desc={sortDesc} onSort={toggleSort} align="right" />
              <Th label="1W %"    sk="1W"     cur={sortKey} desc={sortDesc} onSort={toggleSort} align="right" />
              <Th label="1M %"    sk="1M"     cur={sortKey} desc={sortDesc} onSort={toggleSort} align="right" />
              <Th label="3M %"    sk="3M"     cur={sortKey} desc={sortDesc} onSort={toggleSort} align="right" />
              <Th label="6M %"    sk="6M"     cur={sortKey} desc={sortDesc} onSort={toggleSort} align="right" />
              <Th label="RSI 14"  sk="rsi"    cur={sortKey} desc={sortDesc} onSort={toggleSort} align="right" />
              <Th label="ADX 14"  sk="adx"    cur={sortKey} desc={sortDesc} onSort={toggleSort} align="right" />
              <Th label="Score"   sk="score"  cur={sortKey} desc={sortDesc} onSort={toggleSort} align="right" />
              <Th label="Rec"     sk="rec"    cur={sortKey} desc={sortDesc} onSort={toggleSort} />
              <th className="px-4 py-3 font-medium text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">Signals</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {rows.map((s) => {
              const rsiVal = s.indicators?.rsi_14 as number | undefined
              const adxVal = s.indicators?.adx_14 as number | undefined
              const high52 = is52wHigh(s)
              return (
                <tr key={s.symbol} className={`hover:bg-[var(--color-surface-2)]/40 transition-colors ${high52 ? 'bg-[var(--color-brand-500)]/3' : ''}`}>
                  <td className="px-4 py-2.5">
                    <StockBadge stock={s} />
                  </td>
                  <td className="px-4 py-2.5 text-[var(--color-text-muted)] text-xs whitespace-nowrap">{s.sector ?? '—'}</td>
                  <td className="px-4 py-2.5 text-right font-mono text-xs">
                    {s.close != null ? `₹${s.close.toLocaleString('en-IN')}` : '—'}
                  </td>
                  <PctCell value={s.returns?.['1D']} />
                  <PctCell value={s.returns?.['1W']} />
                  <PctCell value={s.returns?.['1M']} />
                  <PctCell value={s.returns?.['3M']} />
                  <PctCell value={s.returns?.['6M']} />
                  <td className="px-4 py-2.5 text-right font-mono text-xs">
                    {rsiVal != null ? (
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                        rsiVal >= 70 ? 'bg-[var(--color-danger)]/15 text-[var(--color-danger)]'
                        : rsiVal <= 30 ? 'bg-[var(--color-success)]/15 text-[var(--color-success)]'
                        : 'text-[var(--color-text-secondary)]'
                      }`}>{rsiVal.toFixed(1)}</span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-xs">
                    {adxVal != null ? (
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                        adxVal >= 25 ? 'bg-[var(--color-brand-500)]/15 text-[var(--color-brand-400)]'
                        : 'text-[var(--color-text-muted)]'
                      }`}>{adxVal.toFixed(1)}</span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono font-semibold text-xs">
                    {s.score != null ? s.score.toFixed(1) : '—'}
                  </td>
                  <td className="px-4 py-2.5">
                    <RecBadge rec={s.recommendation} />
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {(s.signals ?? []).slice(0, 3).map((sig) => (
                        <span
                          key={sig}
                          className="text-[9px] px-1 py-0.5 rounded bg-[var(--color-surface-2)] text-[var(--color-text-secondary)] whitespace-nowrap"
                        >
                          {sig.replaceAll('_', ' ')}
                        </span>
                      ))}
                      {(s.signals ?? []).length > 3 && (
                        <span className="text-[9px] text-[var(--color-text-muted)]">+{(s.signals ?? []).length - 3}</span>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
            {!isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={13} className="px-4 py-12 text-center text-[var(--color-text-muted)]">
                  No stocks match the current filters.
                  <button onClick={resetFilters} className="ml-2 text-[var(--color-brand-400)] underline text-xs">Reset filters</button>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-2 text-xs text-[var(--color-text-muted)]">
          <div>
            Showing {(currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, allRows.length)} of {allRows.length.toLocaleString()}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1.5 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[var(--color-surface-3)] transition-colors"
            >Previous</button>
            <span className="font-mono">Page {currentPage} / {totalPages}</span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1.5 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[var(--color-surface-3)] transition-colors"
            >Next</button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Sub-components ──────────────────────────────────────────────────────────

function NumFilterInput({
  label, filter, onChange, min, max,
}: {
  label: string
  filter: NumFilter
  onChange: (f: NumFilter) => void
  min?: number
  max?: number
}) {
  const ops: Operator[] = ['>', '>=', '<', '<=', '=']
  return (
    <div>
      <label className="block text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-1">{label}</label>
      <div className="flex gap-1">
        <select
          value={filter.op}
          onChange={(e) => onChange({ ...filter, op: e.target.value as Operator })}
          className="w-14 px-1.5 py-2 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] text-sm font-mono focus:outline-none focus:border-[var(--color-brand-500)] transition-all"
        >
          {ops.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
        <input
          type="number"
          value={filter.val}
          onChange={(e) => onChange({ ...filter, val: e.target.value })}
          placeholder={`${min ?? 0}–${max ?? 100}`}
          min={min}
          max={max}
          className="flex-1 px-2 py-2 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] text-sm font-mono focus:outline-none focus:border-[var(--color-brand-500)] focus:ring-1 focus:ring-[var(--color-brand-500)]/30 transition-all"
        />
      </div>
    </div>
  )
}

function Th({
  label, sk, cur, desc, onSort, align,
}: {
  label: string; sk: SortKey; cur: SortKey; desc: boolean
  onSort: (k: SortKey) => void; align?: 'right'
}) {
  const active = cur === sk
  return (
    <th
      className={`px-4 py-3 font-medium text-[10px] uppercase tracking-wider cursor-pointer select-none whitespace-nowrap transition-colors ${
        active ? 'text-[var(--color-brand-400)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
      } ${align === 'right' ? 'text-right' : 'text-left'}`}
      onClick={() => onSort(sk)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {active && (desc ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />)}
      </span>
    </th>
  )
}

function PctCell({ value }: { value: number | null | undefined }) {
  if (value == null) return <td className="px-4 py-2.5 text-right font-mono text-xs text-[var(--color-text-muted)]">—</td>
  const positive = value >= 0
  return (
    <td className={`px-4 py-2.5 text-right font-mono text-xs ${positive ? 'text-[var(--color-success)]' : 'text-[var(--color-danger)]'}`}>
      {positive ? '+' : ''}{value.toFixed(1)}%
    </td>
  )
}

function RecBadge({ rec }: { rec: string | null }) {
  if (!rec) return <span className="text-[var(--color-text-muted)] text-xs">—</span>
  const cls =
    rec === 'BUY' ? 'bg-[var(--color-success)]/15 text-[var(--color-success)]'
    : rec === 'SELL' ? 'bg-[var(--color-danger)]/15 text-[var(--color-danger)]'
    : 'bg-[var(--color-surface-2)] text-[var(--color-text-muted)]'
  return <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${cls}`}>{rec}</span>
}
