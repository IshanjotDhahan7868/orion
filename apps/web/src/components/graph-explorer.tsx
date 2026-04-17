'use client'

import dynamic from 'next/dynamic'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false })

type ExplorerNode = {
  id: string
  label: string
  kind: 'node' | 'asset'
  theme: string
  type: string
  description?: string
  affects?: string[]
  assetType?: string
  active?: boolean
  score?: number
}

type ExplorerLink = {
  source: string
  target: string
  type: 'causal' | 'exposure'
  weight?: number
  lag_months?: number
  active?: boolean
}

const THEME_COLORS: Record<string, string> = {
  AI: '#38bdf8',
  Semiconductors: '#60a5fa',
  Energy: '#f59e0b',
  Infrastructure: '#34d399',
  Defense: '#f87171',
  Commodities: '#fbbf24',
  Geopolitics: '#c084fc',
  Software: '#22d3ee',
  Financials: '#10b981',
  Industrials: '#fb7185',
  Consumer: '#f97316',
  UNMAPPED: '#71717a',
}

function colorForTheme(theme: string): string {
  return THEME_COLORS[theme] ?? '#71717a'
}

export function GraphExplorer({
  nodes,
  links,
}: {
  nodes: ExplorerNode[]
  links: ExplorerLink[]
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 960, height: 420 })
  const [selectedId, setSelectedId] = useState<string | null>(nodes.find(node => node.active)?.id ?? nodes[0]?.id ?? null)

  useEffect(() => {
    function updateSize() {
      const width = containerRef.current?.clientWidth ?? 960
      setSize({ width, height: 420 })
    }
    updateSize()
    window.addEventListener('resize', updateSize)
    return () => window.removeEventListener('resize', updateSize)
  }, [])

  const selectedNode = useMemo(
    () => nodes.find(node => node.id === selectedId) ?? null,
    [nodes, selectedId]
  )

  const selectedLinks = useMemo(
    () =>
      selectedNode
        ? links.filter(link => link.source === selectedNode.id || link.target === selectedNode.id).slice(0, 10)
        : [],
    [links, selectedNode]
  )

  const graphData = useMemo(() => ({ nodes, links }), [nodes, links])
  const activeNodeCount = nodes.filter(node => node.active).length

  return (
    <div className="grid grid-cols-[minmax(0,1fr)_320px] gap-3">
      <Card ref={containerRef} className="border-zinc-800 bg-zinc-950/80 p-0 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800/60 bg-zinc-900/50">
          <div>
            <p className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono">World Graph</p>
            <p className="text-xs text-zinc-400 mt-1">
              {nodes.length} entities · {links.length} links · {activeNodeCount} live nodes highlighted
            </p>
          </div>
          <div className="flex gap-1.5 flex-wrap justify-end">
            {Object.entries(THEME_COLORS).slice(0, 6).map(([theme, color]) => (
              <span key={theme} className="inline-flex items-center gap-1 text-[10px] text-zinc-500 font-mono">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                {theme}
              </span>
            ))}
          </div>
        </div>

        <ForceGraph2D
          width={size.width}
          height={size.height}
          graphData={graphData}
          backgroundColor="#09090b"
          cooldownTicks={120}
          nodeRelSize={6}
          linkDirectionalParticles={2}
          linkDirectionalParticleSpeed={link => (link.active ? 0.01 : 0.002)}
          linkDirectionalParticleWidth={link => (link.active ? 2.5 : 0.5)}
          onNodeClick={node => setSelectedId((node as ExplorerNode).id)}
          nodeLabel={node => {
            const n = node as ExplorerNode
            return `${n.label} (${n.kind})`
          }}
          linkColor={link => ((link as ExplorerLink).active ? '#f8fafc' : (link as ExplorerLink).type === 'causal' ? 'rgba(148,163,184,0.28)' : 'rgba(34,197,94,0.18)')}
          linkWidth={link => ((link as ExplorerLink).active ? 1.8 : (link as ExplorerLink).type === 'causal' ? 0.5 : 0.35)}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const n = node as ExplorerNode
            const label = n.label
            const fontSize = Math.max(8, 12 / globalScale)
            const radius = n.kind === 'asset' ? 3.8 : 5.5
            const color = colorForTheme(n.theme)

            if (n.active) {
              ctx.beginPath()
              ctx.arc(n.x ?? 0, n.y ?? 0, radius * 2.6, 0, 2 * Math.PI, false)
              ctx.fillStyle = 'rgba(250, 204, 21, 0.12)'
              ctx.fill()
            }

            ctx.beginPath()
            ctx.arc(n.x ?? 0, n.y ?? 0, n.active ? radius * 1.35 : radius, 0, 2 * Math.PI, false)
            ctx.fillStyle = color
            ctx.fill()

            if (n.active || n.kind === 'node') {
              ctx.font = `${fontSize}px ui-monospace, SFMono-Regular, Menlo, monospace`
              ctx.fillStyle = n.active ? '#f8fafc' : 'rgba(226,232,240,0.85)'
              ctx.fillText(label, (n.x ?? 0) + radius + 2, (n.y ?? 0) + radius + 2)
            }
          }}
        />
      </Card>

      <Card className="border-zinc-800 bg-zinc-900/60 p-4 flex flex-col gap-3">
        {selectedNode ? (
          <>
            <div>
              <p className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono">Selection</p>
              <div className="mt-2 flex items-center gap-2 flex-wrap">
                <h3 className="text-zinc-100 text-sm font-semibold">{selectedNode.label}</h3>
                <Badge variant="outline" className="text-[10px] border-zinc-700 text-zinc-400 bg-zinc-950">
                  {selectedNode.kind}
                </Badge>
                <Badge variant="outline" className="text-[10px]" style={{ borderColor: colorForTheme(selectedNode.theme), color: colorForTheme(selectedNode.theme) }}>
                  {selectedNode.theme}
                </Badge>
              </div>
              <p className="text-zinc-500 text-xs mt-2">{selectedNode.description ?? selectedNode.type}</p>
            </div>

            {selectedNode.affects?.length ? (
              <div>
                <p className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono">What Affects It</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {selectedNode.affects.slice(0, 6).map(item => (
                    <Badge key={item} variant="outline" className="text-[10px] border-zinc-700 text-zinc-400">
                      {item}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : null}

            <div>
              <p className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono">Connected Links</p>
              <div className="mt-2 space-y-1.5 max-h-52 overflow-y-auto pr-1">
                {selectedLinks.length ? selectedLinks.map((link, idx) => (
                  <div key={`${link.source}-${link.target}-${idx}`} className="rounded border border-zinc-800 bg-zinc-950/70 p-2">
                    <p className="text-zinc-200 text-xs font-mono">
                      {link.source} → {link.target}
                    </p>
                    <p className="text-zinc-500 text-[11px] mt-1">
                      {link.type} {typeof link.weight === 'number' ? `· w=${link.weight.toFixed(2)}` : ''} {typeof link.lag_months === 'number' ? `· lag=${link.lag_months}mo` : ''}
                    </p>
                  </div>
                )) : (
                  <p className="text-zinc-600 text-xs">No connected links found.</p>
                )}
              </div>
            </div>
          </>
        ) : (
          <p className="text-zinc-600 text-xs">Select a node to inspect it.</p>
        )}
      </Card>
    </div>
  )
}
