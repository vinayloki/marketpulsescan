/**
 * Client-side stores — Zustand + localStorage persistence.
 *
 * Namespaced as mps.v1.* per doc 07 §7.3.
 * Schema-versioned with migration functions for forward compatibility.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// ── Settings Store ───────────────────────────────────────────────────

interface SettingsState {
  capital: number
  riskPercent: number
  defaultHorizon: '1D' | '1W' | '1M' | '3M' | '6M' | '1Y'
  setCapital: (capital: number) => void
  setRiskPercent: (percent: number) => void
  setDefaultHorizon: (horizon: SettingsState['defaultHorizon']) => void
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      capital: 1000000,       // ₹10L default (from config/settings.py)
      riskPercent: 1.5,       // 1.5% risk per trade
      defaultHorizon: '1M',
      setCapital: (capital) => set({ capital }),
      setRiskPercent: (percent) => set({ riskPercent: percent }),
      setDefaultHorizon: (horizon) => set({ defaultHorizon: horizon }),
    }),
    {
      name: 'mps.v1.settings',
      version: 1,
    },
  ),
)

// ── Watchlist Store ──────────────────────────────────────────────────

export interface Watchlist {
  id: string
  name: string
  symbols: string[]
  createdAt: string
}

interface WatchlistState {
  watchlists: Watchlist[]
  addWatchlist: (name: string) => void
  removeWatchlist: (id: string) => void
  addSymbol: (watchlistId: string, symbol: string) => void
  removeSymbol: (watchlistId: string, symbol: string) => void
}

export const useWatchlistStore = create<WatchlistState>()(
  persist(
    (set) => ({
      watchlists: [],
      addWatchlist: (name) =>
        set((state) => ({
          watchlists: [
            ...state.watchlists,
            {
              id: crypto.randomUUID(),
              name,
              symbols: [],
              createdAt: new Date().toISOString(),
            },
          ],
        })),
      removeWatchlist: (id) =>
        set((state) => ({
          watchlists: state.watchlists.filter((w) => w.id !== id),
        })),
      addSymbol: (watchlistId, symbol) =>
        set((state) => ({
          watchlists: state.watchlists.map((w) =>
            w.id === watchlistId && !w.symbols.includes(symbol)
              ? { ...w, symbols: [...w.symbols, symbol] }
              : w,
          ),
        })),
      removeSymbol: (watchlistId, symbol) =>
        set((state) => ({
          watchlists: state.watchlists.map((w) =>
            w.id === watchlistId
              ? { ...w, symbols: w.symbols.filter((s) => s !== symbol) }
              : w,
          ),
        })),
    }),
    {
      name: 'mps.v1.watchlists',
      version: 1,
    },
  ),
)

// ── Portfolio Store ──────────────────────────────────────────────────

export interface PortfolioHolding {
  symbol: string
  qty: number
  avgPrice: number
  buyDate: string
  notes: string
}

interface PortfolioState {
  holdings: PortfolioHolding[]
  addHolding: (holding: Omit<PortfolioHolding, 'notes'> & { notes?: string }) => void
  removeHolding: (symbol: string) => void
  updateHolding: (symbol: string, updates: Partial<PortfolioHolding>) => void
}

export const usePortfolioStore = create<PortfolioState>()(
  persist(
    (set) => ({
      holdings: [],
      addHolding: (holding) =>
        set((state) => ({
          holdings: [
            ...state.holdings,
            { ...holding, notes: holding.notes ?? '' },
          ],
        })),
      removeHolding: (symbol) =>
        set((state) => ({
          holdings: state.holdings.filter((h) => h.symbol !== symbol),
        })),
      updateHolding: (symbol, updates) =>
        set((state) => ({
          holdings: state.holdings.map((h) =>
            h.symbol === symbol ? { ...h, ...updates } : h,
          ),
        })),
    }),
    {
      name: 'mps.v1.portfolio',
      version: 1,
    },
  ),
)
