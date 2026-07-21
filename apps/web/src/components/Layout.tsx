import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard,
  Search,
  Sparkles,
  PieChart,
  Activity,
} from 'lucide-react'
import { useManifest } from '../api/client'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/scanner', label: 'Scanner', icon: Search },
  { to: '/ai-picks', label: 'AI Picks', icon: Sparkles },
  { to: '/sectors', label: 'Sectors', icon: PieChart },
] as const

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <header className="glass sticky top-0 z-50 border-b border-[var(--color-border)]">
        <div className="mx-auto max-w-[1440px] flex items-center justify-between px-4 h-14">
          {/* Logo */}
          <NavLink
            to="/"
            className="flex items-center gap-2 font-bold text-lg tracking-tight"
          >
            <Activity className="h-5 w-5 text-[var(--color-brand-400)]" />
            <span className="text-gradient">MarketPulse</span>
            <span className="text-[var(--color-text-muted)] text-xs font-normal ml-1 hidden sm:inline">
              Scan
            </span>
          </NavLink>

          {/* Nav */}
          <nav className="flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-md)] text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'bg-[var(--color-brand-500)]/15 text-[var(--color-brand-300)]'
                      : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-3)]'
                  }`
                }
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>

          {/* Right side */}
          <div className="flex items-center gap-2">
            <DataFreshnessBadge />
            <a
              href="https://github.com/vinayloki/marketpulsescan"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-3)] transition-colors"
              aria-label="GitHub repository"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
            </a>
          </div>
        </div>
      </header>

      {/* ── Main Content ────────────────────────────────────────────── */}
      <main className="flex-1 mx-auto max-w-[1440px] w-full px-4 py-6 animate-fade-in">
        <Outlet />
      </main>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="border-t border-[var(--color-border)] py-4 px-4">
        <div className="mx-auto max-w-[1440px] flex items-center justify-between text-xs text-[var(--color-text-muted)]">
          <span>MarketPulseScan — Zero-cost Indian stock analysis</span>
          <span>Data refreshed nightly at 16:15 IST</span>
        </div>
      </footer>
    </div>
  )
}

/** Shows data freshness based on manifest.json */
function DataFreshnessBadge() {
  const { data: manifest, isLoading } = useManifest()

  if (isLoading) {
    return (
      <div className="h-6 w-24 rounded-[var(--radius-sm)] bg-[var(--color-surface-2)] animate-pulse" />
    )
  }

  const generatedAt = manifest?.generated_at
  const runId = manifest?.run_id

  let label = 'No data'
  let dotColor = 'var(--color-danger)'

  if (generatedAt) {
    const ageMs = Date.now() - new Date(generatedAt).getTime()
    const ageH = ageMs / 3_600_000
    if (ageH < 26) {
      label = 'Live'
      dotColor = 'var(--color-success)'
    } else if (ageH < 48) {
      label = `${Math.round(ageH)}h ago`
      dotColor = 'var(--color-warning)'
    } else {
      label = `${Math.round(ageH / 24)}d ago`
      dotColor = 'var(--color-danger)'
    }
  }

  const title = generatedAt
    ? `Scan: ${runId ?? '?'} · Generated: ${new Date(generatedAt).toLocaleString()}`
    : 'No manifest data'

  return (
    <div
      title={title}
      className="flex items-center gap-1.5 px-2 py-1 rounded-[var(--radius-sm)] bg-[var(--color-surface-2)] text-xs text-[var(--color-text-muted)] cursor-default"
    >
      <span className="h-1.5 w-1.5 rounded-full animate-pulse" style={{ background: dotColor }} />
      <span className="hidden md:inline">{label}</span>
    </div>
  )
}
