/**
 * Lightweight-charts v5 price chart for StockDetailPage.
 * v5 API: chart.addSeries(areaSeries, options) — NOT addAreaSeries().
 * Builds synthetic price trail from the stock's return percentages.
 */
import { useEffect, useRef, useMemo } from 'react'
import { createChart, ColorType, CrosshairMode, AreaSeries } from 'lightweight-charts'
import type { MarketStock } from '../api/client'

// ── Synthetic price trail builder ─────────────────────────────────────────
function buildPriceTrail(stock: MarketStock): { time: string; value: number }[] {
  const close = stock.close
  if (!close) return []

  const r = stock.returns ?? {}

  // Map each return period to trading days ago
  const anchors: Array<{ daysAgo: number; retPct: number | null | undefined }> = [
    { daysAgo: 252, retPct: r['12M'] as number },
    { daysAgo: 126, retPct: r['6M']  as number },
    { daysAgo: 63,  retPct: r['3M']  as number },
    { daysAgo: 21,  retPct: r['1M']  as number },
    { daysAgo: 5,   retPct: r['1W']  as number },
    { daysAgo: 1,   retPct: r['1D']  as number },
    { daysAgo: 0,   retPct: 0 },
  ]

  const today = new Date()

  const nthBusinessDayBefore = (n: number): Date => {
    const d = new Date(today)
    let skipped = 0
    while (skipped < n) {
      d.setDate(d.getDate() - 1)
      if (d.getDay() !== 0 && d.getDay() !== 6) skipped++
    }
    return d
  }

  const points: { time: string; value: number }[] = []

  for (const { daysAgo, retPct } of anchors) {
    if (retPct == null || isNaN(Number(retPct))) continue
    const historicalPrice = close / (1 + Number(retPct) / 100)
    const d = daysAgo === 0 ? today : nthBusinessDayBefore(daysAgo)
    points.push({
      time: d.toISOString().split('T')[0],
      value: Math.round(historicalPrice * 100) / 100,
    })
  }

  // Deduplicate by time (keep last), sort ascending
  const seen = new Map<string, number>()
  for (const p of points) seen.set(p.time, p.value)
  return Array.from(seen.entries())
    .map(([time, value]) => ({ time, value }))
    .sort((a, b) => a.time.localeCompare(b.time))
}

// ── Chart component ───────────────────────────────────────────────────────
export function PriceChart({ stock }: { stock: MarketStock }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const priceData = useMemo(() => buildPriceTrail(stock), [stock])
  const up = (stock.returns?.['1D'] ?? 0) >= 0

  useEffect(() => {
    const container = containerRef.current
    if (!container || priceData.length < 2) return

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 260,
      layout: {
        background: { type: ColorType.Solid, color: 'rgba(0,0,0,0)' },
        textColor: '#6b7280',
        fontFamily: 'JetBrains Mono, Fira Code, monospace',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: '#1f2937' },
        horzLines: { color: '#1f2937' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: 'rgba(99,102,241,0.6)', width: 1, style: 2 },
        horzLine: { color: 'rgba(99,102,241,0.6)', width: 1, style: 2 },
      },
      rightPriceScale: {
        borderColor: '#374151',
        scaleMargins: { top: 0.08, bottom: 0.08 },
      },
      timeScale: {
        borderColor: '#374151',
        timeVisible: true,
      },
    })

    const lineColor  = up ? '#10b981' : '#ef4444'
    const areaTop    = up ? 'rgba(16,185,129,0.22)' : 'rgba(239,68,68,0.22)'
    const areaBottom = up ? 'rgba(16,185,129,0.01)' : 'rgba(239,68,68,0.01)'

    // v5 API: chart.addSeries(seriesDefinition, options)
    const series = chart.addSeries(AreaSeries, {
      lineColor,
      topColor: areaTop,
      bottomColor: areaBottom,
      lineWidth: 2,
      priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
    })

    series.setData(priceData)
    chart.timeScale().fitContent()

    const ro = new ResizeObserver(() => {
      if (container) chart.applyOptions({ width: container.clientWidth })
    })
    ro.observe(container)

    return () => { ro.disconnect(); chart.remove() }
  }, [priceData, up])

  if (priceData.length < 2) {
    return (
      <div className="flex items-center justify-center h-[260px] text-[var(--color-text-muted)] text-sm">
        Insufficient return data for chart
      </div>
    )
  }

  return (
    <div ref={containerRef} className="w-full rounded-[var(--radius-sm)] overflow-hidden" />
  )
}
