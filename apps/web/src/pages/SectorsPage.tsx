import { PieChart } from 'lucide-react'

export function SectorsPage() {
  return (
    <div className="space-y-6 animate-slide-up">
      <div>
        <div className="flex items-center gap-2">
          <PieChart className="h-5 w-5 text-[var(--color-brand-400)]" />
          <h1 className="text-2xl font-bold tracking-tight">Sectors</h1>
        </div>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">
          Sector rotation, leadership, money flow, and strength ranking
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass rounded-[var(--color-radius-lg)] p-5 rounded-xl">
          <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4">
            Rotation Quadrants (RRG)
          </h2>
          <div className="flex items-center justify-center h-64 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] text-[var(--color-text-muted)] text-sm">
            RS-Ratio vs RS-Momentum scatter plot
          </div>
        </div>
        <div className="glass rounded-xl p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4">
            Sector Strength Ranking
          </h2>
          <div className="flex items-center justify-center h-64 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] text-[var(--color-text-muted)] text-sm">
            Ranked sector bars connected in Sprint 4
          </div>
        </div>
      </div>
    </div>
  )
}
