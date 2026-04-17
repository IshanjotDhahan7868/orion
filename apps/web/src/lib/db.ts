import fs from 'fs/promises'
import path from 'path'

export interface Signal {
  id: number
  event_id: string
  asset: string
  rank: number
  score_raw: number
  score_norm: number
  why_path: string
  when_months: number
  confirmed: boolean
  risk_flags_json: string
  adjusted_score: number
  graph_version: string
  created_at: string
  headline?: string
  event_type?: string
}

export interface Event {
  id: number
  event_type: string
  seeded_nodes_json: string
  confidence: number
  rationale: string
  parser_source: string
  created_at: string
  headline?: string
}

export interface PortfolioPosition {
  asset: string
  weight: number
  theme: string
  score: number
  why_path: string
  lag_months: number
  confirmed: boolean
  event_type?: string | null
}

export interface PortfolioSnapshot {
  snapshot_id: number
  label: string
  summary: {
    count: number
    gross_exposure: number
    average_score: number
    confirmed_only?: boolean
    theme_exposure?: Record<string, number>
    constraints?: Record<string, number>
  }
  positions: PortfolioPosition[]
  created_at: string
}

export interface Watchlist {
  name: string
  assets: string[]
  notes: string
  updated_at: string
}

export interface AnalystBrief {
  brief_id: number
  brief_date: string
  title: string
  body: string
  metadata: Record<string, unknown>
  created_at: string
}

function getEngineUrl(): string {
  return process.env.ORION_ENGINE_URL || 'http://localhost:8000'
}

async function tryFetchJson<T>(pathname: string): Promise<T | null> {
  try {
    const res = await fetch(`${getEngineUrl()}${pathname}`, { cache: 'no-store' })
    if (!res.ok) return null
    return (await res.json()) as T
  } catch {
    return null
  }
}

function getRepoRoot(): string {
  if (process.env.ORION_ROOT_DIR) return process.env.ORION_ROOT_DIR
  return path.resolve(/* turbopackIgnore: true */ process.cwd(), '..', '..')
}

async function readLocalJson<T>(relativePath: string): Promise<T | null> {
  try {
    const raw = await fs.readFile(path.join(getRepoRoot(), relativePath), 'utf-8')
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

async function readLocalCsv(relativePath: string): Promise<Record<string, string>[] | null> {
  try {
    const raw = await fs.readFile(path.join(getRepoRoot(), relativePath), 'utf-8')
    const [headerLine, ...lines] = raw.trim().split(/\r?\n/)
    if (!headerLine) return []
    const headers = headerLine.split(',')
    return lines
      .filter(Boolean)
      .map(line => {
        const values = line.split(',')
        return headers.reduce<Record<string, string>>((acc, header, idx) => {
          acc[header] = values[idx] ?? ''
          return acc
        }, {})
      })
  } catch {
    return null
  }
}

function normalizeSignal(row: Record<string, unknown>, idx: number): Signal {
  const adjustedScore = Number(row.adjusted_score ?? row.adj_score ?? row.score_norm ?? 0)
  const rawRisks = row.risk_flags_json ?? row.risk_flags ?? []
  const riskFlagsJson =
    typeof rawRisks === 'string' ? rawRisks : JSON.stringify(rawRisks)

  return {
    id: Number(row.id ?? idx + 1),
    event_id: String(row.event_id ?? ''),
    asset: String(row.asset ?? ''),
    rank: Number(row.rank ?? idx + 1),
    score_raw: Number(row.score_raw ?? row.score_norm ?? adjustedScore ?? 0),
    score_norm: Number(row.score_norm ?? adjustedScore ?? 0),
    why_path: String(row.why_path ?? ''),
    when_months: Number(row.when_months ?? 0),
    confirmed: Boolean(row.confirmed ?? (row.market_status === 'ok')),
    risk_flags_json: riskFlagsJson,
    adjusted_score: adjustedScore,
    graph_version: String(row.graph_version ?? 'v1.1'),
    created_at: String(row.created_at ?? row.timestamp ?? row.batch_id ?? ''),
    headline: typeof row.headline === 'string' ? row.headline : undefined,
    event_type: typeof row.event_type === 'string' ? row.event_type : undefined,
  }
}

function normalizeEvent(row: Record<string, unknown>, idx: number): Event {
  const seededNodes =
    typeof row.seeded_nodes_json === 'string'
      ? row.seeded_nodes_json
      : JSON.stringify(row.seeded_nodes ?? row.affected_nodes ?? [])

  return {
    id: Number(row.id ?? idx + 1),
    event_type: String(row.event_type ?? 'unknown'),
    seeded_nodes_json: seededNodes,
    confidence: Number(row.confidence ?? 0),
    rationale: String(row.rationale ?? row.summary ?? row.headline ?? ''),
    parser_source: String(row.parser_source ?? row.source ?? 'orion-engine'),
    created_at: String(row.created_at ?? row.published_at ?? ''),
    headline: typeof row.headline === 'string' ? row.headline : undefined,
  }
}

export async function getLatestSignals(limit = 50): Promise<Signal[]> {
  const apiPayload = await tryFetchJson<{ signals: Record<string, unknown>[] }>('/api/signals?limit=200')
  if (apiPayload?.signals) {
    return apiPayload.signals.slice(0, limit).map(normalizeSignal)
  }

  const localJson = await readLocalJson<Record<string, unknown>[] | { signals: Record<string, unknown>[] }>(
    'data/processed/signals_v1_2.json'
  )
  const rows = Array.isArray(localJson) ? localJson : (localJson?.signals ?? [])
  if (rows.length) return rows.slice(0, limit).map(normalizeSignal)

  const csvRows = await readLocalCsv('data/processed/signals_week6.csv')
  return (csvRows ?? []).slice(0, limit).map(normalizeSignal)
}

export async function getLatestEvents(limit = 20): Promise<Event[]> {
  const apiPayload = await tryFetchJson<{ events: Record<string, unknown>[] }>('/api/events?limit=100')
  if (apiPayload?.events) {
    return apiPayload.events.slice(0, limit).map(normalizeEvent)
  }

  const localJson = await readLocalJson<Record<string, unknown>[] | { events: Record<string, unknown>[] }>(
    'data/processed/events.json'
  )
  const rows = Array.isArray(localJson) ? localJson : (localJson?.events ?? [])
  return rows.slice(0, limit).map(normalizeEvent)
}

export async function getLatestPortfolioSnapshot(): Promise<PortfolioSnapshot | null> {
  const payload = await tryFetchJson<PortfolioSnapshot>('/api/portfolio/latest')
  return payload ?? null
}

export async function getWatchlists(): Promise<Watchlist[]> {
  const payload = await tryFetchJson<{ watchlists: Watchlist[] }>('/api/watchlists')
  return payload?.watchlists ?? []
}

export async function getLatestBrief(): Promise<AnalystBrief | null> {
  const payload = await tryFetchJson<AnalystBrief>('/api/briefs/latest')
  return payload ?? null
}

export async function getTopSignalsContext(limit = 30): Promise<string> {
  const signals = await getLatestSignals(limit)
  if (!signals.length) return 'No signals generated yet.'

  return signals
    .map(s =>
      `${s.asset}: score=${s.adjusted_score?.toFixed(2)}, path="${s.why_path}", lag=${s.when_months}mo, confirmed=${s.confirmed}, risks=${s.risk_flags_json || '[]'}`
    )
    .join('\n')
}

export async function getRecentEventsContext(limit = 20): Promise<string> {
  const events = await getLatestEvents(limit)
  if (!events.length) return 'No events processed yet.'

  return events
    .map(e =>
      `[${e.event_type}] ${e.headline || e.rationale} (confidence=${e.confidence?.toFixed(2)}, nodes=${e.seeded_nodes_json})`
    )
    .join('\n')
}
