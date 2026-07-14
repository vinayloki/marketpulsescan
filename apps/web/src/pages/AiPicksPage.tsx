import { Sparkles } from 'lucide-react'

export function AiPicksPage() {
  return (
    <div className="space-y-6 animate-slide-up">
      <div>
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-[var(--color-brand-400)]" />
          <h1 className="text-2xl font-bold tracking-tight">AI Picks</h1>
        </div>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">
          Top-ranked opportunities — 5-component composite score, backtest-calibrated
        </p>
      </div>

      <div className="glass rounded-[var(--radius-lg)] overflow-hidden">
        <div className="px-4 py-3 border-b border-[var(--color-border)]">
          <span className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
            Ranked Picks
          </span>
        </div>
        <div className="flex items-center justify-center h-64 text-[var(--color-text-muted)] text-sm">
          AI picks table connected in Sprint 4 (Story 4.5)
        </div>
      </div>
    </div>
  )
}
