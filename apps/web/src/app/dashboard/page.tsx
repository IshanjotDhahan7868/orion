import { getLatestSignals, getLatestEvents, getLatestPortfolioSnapshot, getLatestBrief, getWatchlists } from '@/lib/db'
import { getGraphEdges, getGraphNodes, getAssetMappings } from '@/lib/graph'

export const dynamic = 'force-dynamic'
import { SignalsTable } from '@/components/signals-table'
import { OrionChat } from '@/components/chat'
import { GraphExplorer } from '@/components/graph-explorer'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'

function EventTypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    capex_expansion: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
    supply_constraint: 'text-orange-400 border-orange-500/30 bg-orange-500/10',
    demand_surge: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10',
    regulatory: 'text-purple-400 border-purple-500/30 bg-purple-500/10',
    geopolitical: 'text-red-400 border-red-500/30 bg-red-500/10',
  }
  const cls = colors[type] ?? 'text-zinc-400 border-zinc-700 bg-zinc-800/50'
  return (
    <Badge variant="outline" className={`text-xs font-mono ${cls}`}>
      {type?.replace(/_/g, ' ')}
    </Badge>
  )
}

function buildExplorerData(signals: Awaited<ReturnType<typeof getLatestSignals>>) {
  const graphNodes = getGraphNodes()
  const graphEdges = getGraphEdges()
  const assetMappings = getAssetMappings()

  const activeNodeIds = new Set<string>()
  const activeAssets = new Set<string>()
  const signalScores = new Map<string, number>()

  for (const signal of signals.slice(0, 15)) {
    activeAssets.add(signal.asset)
    signalScores.set(signal.asset, signal.adjusted_score)
    for (const part of (signal.why_path || '').split('→').map(p => p.trim()).filter(Boolean)) {
      activeNodeIds.add(part)
    }
  }

  const nodes = [
    ...graphNodes.map(node => ({
      id: node.id,
      label: node.id,
      kind: 'node' as const,
      theme: node.theme,
      type: node.type,
      description: node.what_is_this,
      affects: node.what_affects_it,
      active: activeNodeIds.has(node.id),
    })),
    ...Object.entries(assetMappings).map(([asset, meta]) => ({
      id: `asset:${asset}`,
      label: asset,
      kind: 'asset' as const,
      theme: meta.nodes[0] ? graphNodes.find(node => node.id === meta.nodes[0])?.theme ?? 'UNMAPPED' : 'UNMAPPED',
      type: meta.type,
      assetType: meta.type,
      description: `${meta.type} mapped to ${meta.nodes.join(', ')}`,
      active: activeAssets.has(asset),
      score: signalScores.get(asset),
    })),
  ]

  const links = [
    ...graphEdges.map(edge => ({
      source: edge.from,
      target: edge.to,
      type: 'causal' as const,
      weight: edge.weight,
      lag_months: edge.lag_months,
      active: activeNodeIds.has(edge.from) && activeNodeIds.has(edge.to),
    })),
    ...Object.entries(assetMappings).flatMap(([asset, meta]) =>
      meta.nodes.map(nodeId => ({
        source: nodeId,
        target: `asset:${asset}`,
        type: 'exposure' as const,
        active: activeAssets.has(asset) && activeNodeIds.has(nodeId),
      }))
    ),
  ]

  return { nodes, links }
}

export default async function DashboardPage() {
  const [signals, events, portfolio, brief, watchlists] = await Promise.all([
    getLatestSignals(50).catch(() => []),
    getLatestEvents(15).catch(() => []),
    getLatestPortfolioSnapshot().catch(() => null),
    getLatestBrief().catch(() => null),
    getWatchlists().catch(() => []),
  ])
  const explorer = buildExplorerData(signals)
  const confirmedCount = signals.filter(signal => signal.confirmed).length
  const avgTopScore =
    signals.length > 0
      ? signals.slice(0, 10).reduce((sum, signal) => sum + signal.adjusted_score, 0) / Math.min(signals.length, 10)
      : 0
  const topSignal = signals[0] ?? null

  return (
    <div className="flex flex-col h-screen bg-zinc-950">
      {/* Header */}
      <header className="border-b border-zinc-800 px-4 py-3 flex items-center gap-4 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-blue-400 font-bold text-lg">⬡</span>
          <span className="font-mono font-bold text-zinc-100 tracking-wider">ORION</span>
          <span className="text-zinc-600 text-xs font-mono">v1.0 / MACRO INTELLIGENCE</span>
        </div>
        <Separator orientation="vertical" className="h-4 bg-zinc-700" />
        <div className="flex items-center gap-3 text-xs font-mono text-zinc-500">
          <span>{signals.length} signals</span>
          <span>·</span>
          <span>{events.length} events</span>
          <span>·</span>
          <span>{confirmedCount} confirmed</span>
          <span>·</span>
          <span className="text-emerald-500">● live</span>
        </div>
      </header>

      {/* Main layout: signals left, chat right */}
      <div className="flex flex-1 min-h-0 divide-x divide-zinc-800">
        {/* Left: Signals + Events */}
        <div className="flex flex-col w-3/5 min-h-0 divide-y divide-zinc-800">
          <div className="mx-4 mt-4 rounded-xl border border-cyan-500/20 bg-cyan-500/8 px-4 py-3 shrink-0">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[10px] uppercase tracking-[0.28em] text-cyan-300 font-mono">Commercial Lens</p>
                <p className="mt-1 text-sm text-zinc-100">
                  This is currently strongest as a high-ticket pilot or research terminal, not broad self-serve SaaS.
                </p>
                <p className="mt-1 text-xs text-zinc-400">
                  To sell harder: prove repeatable signal quality, tighten event freshness, add auth/billing, and show customer-specific workflows.
                </p>
              </div>
              <Badge variant="outline" className="border-cyan-400/30 bg-cyan-400/10 text-cyan-200 text-[10px] font-mono">
                DEMOABLE NOW
              </Badge>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 p-4 border-b border-zinc-800/50 bg-zinc-950/70 shrink-0">
            <Card className="border-zinc-800 bg-zinc-900/60 p-3">
              <p className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono">Portfolio</p>
              {portfolio ? (
                <div className="mt-2 space-y-1.5">
                  <p className="text-zinc-100 text-sm font-semibold">{portfolio.label}</p>
                  <p className="text-zinc-400 text-xs">
                    gross {(portfolio.summary.gross_exposure * 100).toFixed(1)}% · avg score {portfolio.summary.average_score?.toFixed(2)}
                  </p>
                  <div className="flex flex-wrap gap-1 pt-1">
                    {portfolio.positions.slice(0, 4).map(position => (
                      <Badge key={position.asset} variant="outline" className="text-[10px] border-emerald-500/30 text-emerald-300 bg-emerald-500/10">
                        {position.asset} {(position.weight * 100).toFixed(1)}%
                      </Badge>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="mt-2 text-zinc-600 text-xs">No portfolio snapshot yet.</p>
              )}
            </Card>

            <Card className="border-zinc-800 bg-zinc-900/60 p-3">
              <p className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono">Watchlists</p>
              {watchlists.length ? (
                <div className="mt-2 space-y-1.5">
                  <p className="text-zinc-100 text-sm font-semibold">{watchlists[0].name}</p>
                  <p className="text-zinc-400 text-xs">{watchlists.length} active list{watchlists.length === 1 ? '' : 's'}</p>
                  <div className="flex flex-wrap gap-1 pt-1">
                    {watchlists[0].assets.slice(0, 5).map(asset => (
                      <Badge key={asset} variant="outline" className="text-[10px] border-blue-500/30 text-blue-300 bg-blue-500/10">
                        {asset}
                      </Badge>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="mt-2 text-zinc-600 text-xs">No watchlists saved yet.</p>
              )}
            </Card>

            <Card className="border-zinc-800 bg-zinc-900/60 p-3">
              <p className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono">Signal Quality</p>
              {signals.length ? (
                <div className="mt-2 space-y-1.5">
                  <p className="text-zinc-100 text-sm font-semibold">
                    avg top-10 {avgTopScore.toFixed(2)} · {confirmedCount}/{signals.length} confirmed
                  </p>
                  <p className="text-zinc-400 text-xs">
                    strongest live idea: {topSignal?.asset ?? '—'} {topSignal ? topSignal.adjusted_score.toFixed(2) : ''}
                  </p>
                  <div className="flex flex-wrap gap-1 pt-1">
                    {topSignal ? (
                      <Badge variant="outline" className="text-[10px] border-cyan-500/30 text-cyan-300 bg-cyan-500/10">
                        {topSignal.why_path || topSignal.asset}
                      </Badge>
                    ) : null}
                  </div>
                </div>
              ) : (
                <p className="mt-2 text-zinc-600 text-xs">No signals generated yet.</p>
              )}
            </Card>
          </div>

          {brief ? (
            <div className="px-4 pb-4 shrink-0 border-b border-zinc-800/50">
              <Card className="border-zinc-800 bg-zinc-900/60 p-4">
                <p className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono">Analyst Brief</p>
                <p className="mt-2 text-zinc-100 text-sm font-semibold truncate">{brief.title}</p>
                <p className="mt-2 text-zinc-400 text-xs line-clamp-4 whitespace-pre-wrap">
                  {brief.body}
                </p>
              </Card>
            </div>
          ) : null}

          <div className="p-4 border-b border-zinc-800/50 shrink-0">
            <GraphExplorer nodes={explorer.nodes} links={explorer.links} />
          </div>

          {/* Signals table */}
          <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
            <div className="px-4 py-2 border-b border-zinc-800/50 flex items-center gap-2 shrink-0">
              <span className="text-xs font-mono text-zinc-400 uppercase tracking-widest">Signals</span>
              <span className="text-xs text-zinc-600">— ranked by causal impact score</span>
            </div>
            <div className="overflow-y-auto flex-1">
              <SignalsTable signals={signals} />
            </div>
          </div>

          {/* Recent events */}
          <div className="h-56 overflow-hidden flex flex-col shrink-0">
            <div className="px-4 py-2 border-b border-zinc-800/50 shrink-0">
              <span className="text-xs font-mono text-zinc-400 uppercase tracking-widest">Recent Events</span>
            </div>
            <div className="overflow-y-auto flex-1 p-2 space-y-1.5">
              {events.length === 0 ? (
                <p className="text-zinc-600 text-xs p-2">No events yet. Run the pipeline.</p>
              ) : (
                events.map(e => (
                  <div key={e.id} className="flex items-start gap-2 px-2 py-1.5 rounded hover:bg-zinc-900/50">
                    <EventTypeBadge type={e.event_type} />
                    <div className="flex-1 min-w-0">
                      <p className="text-zinc-300 text-xs truncate">
                        {e.headline ?? e.rationale}
                      </p>
                      <p className="text-zinc-600 text-xs mt-0.5">
                        conf={e.confidence?.toFixed(2)} · nodes={JSON.parse(e.seeded_nodes_json ?? '[]').join(', ')}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right: Chat */}
        <div className="flex flex-col w-2/5 min-h-0">
          <div className="px-4 py-2 border-b border-zinc-800/50 shrink-0">
            <span className="text-xs font-mono text-zinc-400 uppercase tracking-widest">Intelligence Chat</span>
          </div>
          <div className="flex-1 min-h-0">
            <OrionChat />
          </div>
        </div>
      </div>
    </div>
  )
}
