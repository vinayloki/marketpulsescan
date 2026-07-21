import { Link } from 'react-router-dom'
import type { MarketStock } from '../api/client'

export function StockBadge({ stock, showNames = false }: { stock: MarketStock; showNames?: boolean }) {
  const sym = stock.symbol
  const high52 = (stock.indicators?.high_52w as number | undefined) ?? (stock.high_52w as number | undefined)
  const is52wHigh =
    (stock.close != null && high52 != null && stock.close >= high52 * 0.985) ||
    (stock.signals ?? []).includes('52W_HIGH') ||
    (stock.signals ?? []).includes('BREAKOUT_52W_HIGH')

  return (
    <div className="inline-flex items-center gap-1.5 flex-wrap">
      <Link
        to={`/stocks/${sym}`}
        className="font-semibold text-sm hover:text-[var(--color-brand-400)] transition-colors inline-flex items-center gap-1"
      >
        <span>{sym}</span>
        {is52wHigh && (
          <span title="52-Week High Breakout 🚀" className="animate-pulse text-xs">
            🚀
          </span>
        )}
      </Link>
      {showNames && stock.name && (
        <span className="text-xs text-[var(--color-text-muted)] truncate max-w-[140px]">
          {stock.name}
        </span>
      )}
      <div className="inline-flex items-center gap-1 opacity-75 hover:opacity-100 transition-opacity">
        <a
          href={`https://in.tradingview.com/chart/?symbol=BSE:${sym}`}
          target="_blank"
          rel="noopener noreferrer"
          title={`Open ${sym} on TradingView (BSE)`}
          className="text-[10px] font-mono font-semibold px-1 py-0.5 rounded bg-[var(--color-surface-3)] text-[var(--color-brand-400)] hover:bg-[var(--color-brand-500)]/20 transition-colors"
          onClick={(e) => e.stopPropagation()}
        >
          TV
        </a>
        <a
          href={`https://www.screener.in/company/${sym}/`}
          target="_blank"
          rel="noopener noreferrer"
          title={`Open ${sym} on Screener.in`}
          className="text-[10px] font-mono font-semibold px-1 py-0.5 rounded bg-[var(--color-surface-3)] text-[var(--color-brand-400)] hover:bg-[var(--color-brand-500)]/20 transition-colors"
          onClick={(e) => e.stopPropagation()}
        >
          SCR
        </a>
      </div>
    </div>
  )
}
