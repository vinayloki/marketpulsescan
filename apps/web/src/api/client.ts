/**
 * Typed API client for MarketPulseScan static JSON dataset.
 *
 * Generated types will come from JSON Schemas in schemas/v1/ (Sprint 4).
 * For now, this provides the data URL resolution and fetch helpers.
 */

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
  name: string
  sector: string
  mcap_cr: number
  mcap_category: string
  close: number
  returns: Record<string, number>
  recommendation: string
  composite_score: number
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
