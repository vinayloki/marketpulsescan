/**
 * Typed API client for MarketPulseScan static JSON dataset.
 *
 * Generated types will come from JSON Schemas in schemas/v1/ (Sprint 4).
 * For now, this provides the data URL resolution and fetch helpers.
 */

import { useQuery } from '@tanstack/react-query'

/** Base URL for the dataset API — configurable per environment */
const DATA_BASE_URL = import.meta.env.VITE_DATA_URL
  ?? `${import.meta.env.BASE_URL}api/v1`

/** Fetch a JSON file from the static API */
export async function fetchDataset<T>(path: string): Promise<T> {
  const url = `${DATA_BASE_URL}/${path}`
  const res = await fetch(url)

  if (!res.ok) {
    throw new Error(`[API] Failed to fetch ${path}: ${res.status} ${res.statusText}`)
  }

  return res.json() as Promise<T>
}

// ── Dataset types (stubs — generated from schemas in Sprint 4) ───────

export interface Manifest {
  schema_version: string
  generated_at: string
  run_id: string
  files: ManifestFile[]
}

export interface ManifestFile {
  path: string
  checksum: string
  row_count: number
  as_of: string
}

export interface MarketStock {
  symbol: string
  name: string | null
  sector: string | null
  industry?: string | null
  exchange: string
  mcap_cr: number | null
  mcap_category: string | null
  close: number | null
  prev_close: number | null
  volume?: number | null
  volume_avg_20d?: number | null
  high_52w?: number | null
  low_52w?: number | null
  returns: Record<string, number | null>
  // New schema: top-level score + sub_scores dict
  score: number | null
  sub_scores: Record<string, number> | null
  // Legacy schema: scores dict with composite key
  scores?: Record<string, number> | null
  recommendation: string | null
  probabilities?: Record<string, number> | null
  signals: string[]
  indicators: Record<string, number | string | boolean | null> | null
}

export interface MarketData {
  schema_version: string
  generated_at: string
  run_id: string
  data: MarketStock[]
}

// ── Query keys ───────────────────────────────────────────────────────

export const queryKeys = {
  manifest: ['manifest'] as const,
  market: ['market'] as const,
  universe: ['universe'] as const,
  stock: (symbol: string) => ['stock', symbol] as const,
  aiPicks: ['ai-picks'] as const,
  sectors: ['sectors'] as const,
  regime: ['regime'] as const,
  news: ['news'] as const,
} as const

// ── Query hooks ──────────────────────────────────────────────────────

export function useManifest() {
  return useQuery({
    queryKey: queryKeys.manifest,
    queryFn: () => fetchDataset<Manifest>('manifest.json'),
    staleTime: 5 * 60 * 1000,
  })
}

export function useMarket() {
  return useQuery({
    queryKey: queryKeys.market,
    queryFn: () => fetchDataset<MarketData>('market.json'),
    staleTime: 5 * 60 * 1000,
    select: (data) => ({
      ...data,
      // Normalize legacy fixture schema → new schema fields
      data: data.data.map((s) => ({
        ...s,
        score: s.score ?? s.scores?.['composite'] ?? null,
        sub_scores: s.sub_scores ?? (
          s.scores
            ? Object.fromEntries(Object.entries(s.scores).filter(([k]) => k !== 'composite'))
            : null
        ),
        indicators: s.indicators ?? (
          // Lift legacy top-level fields into indicators dict
          (s.high_52w != null || s.low_52w != null)
            ? { high_52w: s.high_52w, low_52w: s.low_52w }
            : null
        ),
      })),
    }),
  })
}
