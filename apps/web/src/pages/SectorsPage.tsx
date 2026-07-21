import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { PieChart, TrendingUp } from 'lucide-react'
import { useMarket } from '../api/client'
import type { MarketStock } from '../api/client'

// ── Sector aggregation ────────────────────────────────────────────────────
interface SectorStats {
  name: string
  count: number
  avgScore: number
  avg1D: number
  avg1W: number
  avg1M: number
  avg3M: number
  avg6M: number
  avg12M: number
  buys: number
  top: MarketStock | null
  color: string
}

const SECTOR_COLORS: Record<string, string> = {
  'Information Technology': 'oklch(0.65 0.19 250)',
  'Financial Services':     'oklch(0.68 0.18 220)',
  'Oil & Gas':              'oklch(0.72 0.15 80)',
  'Automobile':             'oklch(0.65 0.20 155)',
  'Pharmaceuticals':        'oklch(0.62 0.18 170)',
  'FMCG':                   'oklch(0.72 0.14 30)',
  'Metals':                 'oklch(0.60 0.10 280)',
  'Power':                  'oklch(0.72 0.18 50)',
  'Realty':                 'oklch(0.62 0.16 340)',
  'Capital Goods':          'oklch(0.65 0.18 130)',
  'Chemicals':              'oklch(0.68 0.16 190)',
  'Consumer Durables':      'oklch(0.70 0.17 310)',
  'Textiles':               'oklch(0.64 0.14 100)',
}

function sectorColor(name: string) {
  return SECTOR_COLORS[name] ?? 'oklch(0.65 0.18 240)'
}

function aggregateSectors(stocks: MarketStock[]): SectorStats[] {
  const map: Record<string, MarketStock[]> = {}
  for (const s of stocks) {
    const sec = s.sector ?? 'Unknown'
    if (!map[sec]) map[sec] = []
    map[sec].push(s)
  }

  return Object.entries(map).map(([name, ss]) => {
    const scores = ss.map(s => s.score).filter((v): v is number => v != null)
    const ret1d = ss.map(s => s.returns?.['1D']).filter((v): v is number => v != null)
    const ret1w = ss.map(s => s.returns?.['1W']).filter((v): v is number => v != null)
    const ret1m = ss.map(s => s.returns?.['1M']).filter((v): v is number => v != null)
    const ret3m = ss.map(s => s.returns?.['3M']).filter((v): v is number => v != null)
    const ret6m = ss.map(s => s.returns?.['6M']).filter((v): v is number => v != null)
    const ret12m = ss.map(s => s.returns?.['12M']).filter((v): v is number => v != null)
    const avg = (arr: number[]) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0
    return {
      name,
      count: ss.length,
      avgScore: avg(scores),
      avg1D: avg(ret1d),
      avg1W: avg(ret1w),
      avg1M: avg(ret1m),
      avg3M: avg(ret3m),
      avg6M: avg(ret6m),
      avg12M: avg(ret12m),
      buys: ss.filter(s => s.recommendation === 'BUY').length,
      top: ss.sort((a, b) => (b.score ?? 0) - (a.score ?? 0))[0] ?? null,
      color: sectorColor(name),
    }
  }).sort((a, b) => b.avgScore - a.avgScore)
}

// ── Bubble chart (SVG) ────────────────────────────────────────────────────
function BubbleChart({ sectors }: { sectors: SectorStats[] }) {
  const W = 520
  const H = 300
  const PAD = { top: 24, right: 20, bottom: 40, left: 48 }

  const xs = sectors.map(s => s.avg1M)
  const ys = sectors.map(s => s.avgScore)

  const xMin = Math.min(...xs) - 2
  const xMax = Math.max(...xs) + 2
  const yMin = Math.max(0, Math.min(...ys) - 5)
  const yMax = Math.min(100, Math.max(...ys) + 5)

  const scaleX = (v: number) =>
    PAD.left + ((v - xMin) / (xMax - xMin || 1)) * (W - PAD.left - PAD.right)
  const scaleY = (v: number) =>
    PAD.top + (1 - (v - yMin) / (yMax - yMin || 1)) * (H - PAD.top - PAD.bottom)
  const scaleR = (count: number) => Math.max(14, Math.sqrt(count) * 12)

  // Grid lines
  const yTicks = [0, 25, 50, 75, 100].filter(t => t >= yMin && t <= yMax)
  const xTicks = [-10, -5, 0, 5, 10, 15, 20, 25, 30].filter(t => t >= xMin && t <= xMax)

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      style={{ fontFamily: 'var(--font-mono, monospace)' }}
    >
      {/* Grid */}
      {yTicks.map(t => (
        <g key={t}>
          <line x1={PAD.left} y1={scaleY(t)} x2={W - PAD.right} y2={scaleY(t)}
            stroke="oklch(0.28 0.02 260)" strokeWidth={1} />
          <text x={PAD.left - 6} y={scaleY(t)} textAnchor="end" dominantBaseline="middle"
            fill="oklch(0.50 0.02 260)" fontSize={9}>{t}</text>
        </g>
      ))}
      {xTicks.map(t => (
        <g key={t}>
          <line x1={scaleX(t)} y1={PAD.top} x2={scaleX(t)} y2={H - PAD.bottom}
            stroke="oklch(0.28 0.02 260)" strokeWidth={1} strokeDasharray="3 3" />
          <text x={scaleX(t)} y={H - PAD.bottom + 12} textAnchor="middle"
            fill="oklch(0.50 0.02 260)" fontSize={9}>{t > 0 ? `+${t}%` : `${t}%`}</text>
        </g>
      ))}
      {/* Zero line */}
      <line x1={scaleX(0)} y1={PAD.top} x2={scaleX(0)} y2={H - PAD.bottom}
        stroke="oklch(0.38 0.03 260)" strokeWidth={1.5} />

      {/* Axis labels */}
      <text x={(W) / 2} y={H - 4} textAnchor="middle" fill="oklch(0.50 0.02 260)" fontSize={10}>
        1-Month Return %
      </text>
      <text transform={`rotate(-90, 12, ${H / 2})`} x={12} y={H / 2} textAnchor="middle"
        fill="oklch(0.50 0.02 260)" fontSize={10}>
        Score
      </text>

      {/* Bubbles */}
      {sectors.map(sec => {
        const cx = scaleX(sec.avg1M)
        const cy = scaleY(sec.avgScore)
        const r = scaleR(sec.count)
        const shortName = sec.name.length > 10 ? sec.name.slice(0, 9) + '…' : sec.name
        return (
          <g key={sec.name}>
            <circle
              cx={cx} cy={cy} r={r}
              fill={sec.color}
              opacity={0.25}
              stroke={sec.color}
              strokeWidth={1.5}
            />
            <text x={cx} y={cy - 1} textAnchor="middle" dominantBaseline="middle"
              fill={sec.color} fontSize={8} fontWeight="600">
              {shortName}
            </text>
            <text x={cx} y={cy + 9} textAnchor="middle" fill="oklch(0.70 0.02 260)" fontSize={7}>
              {sec.avgScore.toFixed(0)} · {sec.count}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────
export function SectorsPage() {
  const { data: market, isLoading, isError } = useMarket()
  const stocks = market?.data ?? []

  const sectors = useMemo(() => aggregateSectors(stocks), [stocks])
  const maxScore = Math.max(...sectors.map(s => s.avgScore), 1)

  if (isLoading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <Header />
        <div className="h-48 glass rounded-[var(--radius-lg)] animate-pulse" />
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-slide-up">
      <Header />

      {isError && (
        <div className="glass rounded-[var(--radius-lg)] p-4 text-sm text-[var(--color-danger)]">
          Could not load dataset.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Sector Strength Ranking */}
        <div className="glass rounded-[var(--radius-lg)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-5 flex items-center gap-2">
            <PieChart className="h-4 w-4" /> Sector Strength Ranking
          </h2>
          {sectors.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-[var(--color-text-muted)] text-sm">
              No sector data
            </div>
          ) : (
            <div className="space-y-4">
              {sectors.map((sec, i) => (
                <div key={sec.name}>
                  <div className="flex items-start justify-between mb-1.5 gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className="text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center shrink-0"
                        style={{ background: `${sec.color}20`, color: sec.color }}
                      >
                        {i + 1}
                      </span>
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{sec.name}</div>
                        <div className="text-[11px] text-[var(--color-text-muted)]">
                          {sec.count} stock{sec.count !== 1 ? 's' : ''} · {sec.buys} BUY
                          {sec.top && (
                            <span> · Top:{' '}
                              <Link
                                to={`/stocks/${sec.top.symbol}`}
                                className="hover:text-[var(--color-brand-400)] transition-colors"
                              >
                                {sec.top.symbol}
                              </Link>
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-sm font-bold font-mono" style={{ color: sec.color }}>
                        {sec.avgScore.toFixed(0)}
                      </div>
                      <div
                        className="text-[11px] font-mono"
                        style={{ color: sec.avg1M >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}
                      >
                        {sec.avg1M >= 0 ? '+' : ''}{sec.avg1M.toFixed(1)}%
                      </div>
                    </div>
                  </div>
                  <div className="h-2 rounded-full bg-[var(--color-surface-3)] overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${(sec.avgScore / maxScore) * 100}%`,
                        background: sec.color,
                        opacity: 0.85,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Bubble Chart */}
        <div className="glass rounded-[var(--radius-lg)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-4 flex items-center gap-2">
            <TrendingUp className="h-4 w-4" /> Score vs 1M Return (Bubble = stock count)
          </h2>
          {sectors.length < 2 ? (
            <div className="flex items-center justify-center h-48 text-[var(--color-text-muted)] text-sm">
              Need 2+ sectors to plot
            </div>
          ) : (
            <BubbleChart sectors={sectors} />
          )}
        </div>
      </div>

      {/* Sector table */}
      <div className="glass rounded-[var(--radius-lg)] overflow-hidden">
        <div className="px-4 py-3 border-b border-[var(--color-border)]">
          <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
            Sector Detail Table
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left">
                {['Sector', 'Stocks', 'BUYs', 'Avg Score', '1D Avg', '1W Avg', '1M Avg', '3M Avg', '6M Avg', '12M Avg', 'Top Pick'].map(h => (
                  <th key={h} className="px-3 py-3 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)] text-right first:text-left last:text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {sectors.map((sec) => (
                <tr key={sec.name} className="hover:bg-[var(--color-surface-2)]/50 transition-colors">
                  <td className="px-3 py-3 font-medium">
                    <span className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ background: sec.color }} />
                      {sec.name}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-[var(--color-text-muted)] text-right">{sec.count}</td>
                  <td className="px-3 py-3 text-right">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[var(--color-success)]/10 text-[var(--color-success)]">
                      {sec.buys}
                    </span>
                  </td>
                  <td className="px-3 py-3 font-mono font-bold text-right" style={{ color: sec.color }}>
                    {sec.avgScore.toFixed(1)}
                  </td>
                  <td
                    className="px-3 py-3 font-mono text-right"
                    style={{ color: sec.avg1D >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}
                  >
                    {sec.avg1D >= 0 ? '+' : ''}{sec.avg1D.toFixed(1)}%
                  </td>
                  <td
                    className="px-3 py-3 font-mono text-right"
                    style={{ color: sec.avg1W >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}
                  >
                    {sec.avg1W >= 0 ? '+' : ''}{sec.avg1W.toFixed(1)}%
                  </td>
                  <td
                    className="px-3 py-3 font-mono text-right"
                    style={{ color: sec.avg1M >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}
                  >
                    {sec.avg1M >= 0 ? '+' : ''}{sec.avg1M.toFixed(1)}%
                  </td>
                  <td
                    className="px-3 py-3 font-mono text-right"
                    style={{ color: sec.avg3M >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}
                  >
                    {sec.avg3M >= 0 ? '+' : ''}{sec.avg3M.toFixed(1)}%
                  </td>
                  <td
                    className="px-3 py-3 font-mono text-right"
                    style={{ color: sec.avg6M >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}
                  >
                    {sec.avg6M >= 0 ? '+' : ''}{sec.avg6M.toFixed(1)}%
                  </td>
                  <td
                    className="px-3 py-3 font-mono text-right"
                    style={{ color: sec.avg12M >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}
                  >
                    {sec.avg12M >= 0 ? '+' : ''}{sec.avg12M.toFixed(1)}%
                  </td>
                  <td className="px-3 py-3">
                    {sec.top && (
                      <Link
                        to={`/stocks/${sec.top.symbol}`}
                        className="text-xs font-semibold hover:text-[var(--color-brand-400)] transition-colors"
                      >
                        {sec.top.symbol}
                        <span className="ml-1 text-[var(--color-text-muted)] font-normal">
                          {sec.top.score?.toFixed(0)}
                        </span>
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function Header() {
  return (
    <div>
      <div className="flex items-center gap-2">
        <PieChart className="h-5 w-5 text-[var(--color-brand-400)]" />
        <h1 className="text-2xl font-bold tracking-tight">Sectors</h1>
      </div>
      <p className="text-[var(--color-text-secondary)] text-sm mt-1">
        Sector rotation, leadership, money flow, and strength ranking
      </p>
    </div>
  )
}
