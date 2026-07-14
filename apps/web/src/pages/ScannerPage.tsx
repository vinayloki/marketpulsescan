import { Search, SlidersHorizontal } from 'lucide-react'

export function ScannerPage() {
  return (
    <div className="space-y-6 animate-slide-up">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Scanner</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">
            Full universe scan — ~3,000 NSE + BSE stocks
          </p>
        </div>
        <button
          className="flex items-center gap-2 px-3 py-2 rounded-[var(--radius-md)] glass glass-hover text-sm font-medium text-[var(--color-text-secondary)] transition-all"
          disabled
        >
          <SlidersHorizontal className="h-4 w-4" />
          Filters
        </button>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-text-muted)]" />
        <input
          type="text"
          placeholder="Search by ticker, name, or sector..."
          className="w-full pl-10 pr-4 py-2.5 rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-brand-500)] focus:ring-1 focus:ring-[var(--color-brand-500)]/30 transition-all"
          disabled
        />
      </div>

      {/* Table Placeholder */}
      <div className="glass rounded-[var(--radius-lg)] overflow-hidden">
        <div className="px-4 py-3 border-b border-[var(--color-border)]">
          <span className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
            Stock Scanner Table
          </span>
        </div>
        <div className="flex items-center justify-center h-64 text-[var(--color-text-muted)] text-sm">
          Virtualized table connected in Sprint 4 (Story 4.3)
        </div>
      </div>
    </div>
  )
}
