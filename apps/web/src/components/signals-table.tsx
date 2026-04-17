'use client'

import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { Signal } from '@/lib/db'

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 0.8
      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
      : score >= 0.5
      ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
      : 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30'
  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-mono border ${color}`}>
      {score?.toFixed(3)}
    </span>
  )
}

function RiskFlags({ flagsJson }: { flagsJson: string }) {
  let flags: string[] = []
  try {
    flags = JSON.parse(flagsJson || '[]')
  } catch {
    flags = []
  }
  if (!flags.length) return <span className="text-zinc-600 text-xs">—</span>
  return (
    <div className="flex gap-1 flex-wrap">
      {flags.map(f => (
        <Badge key={f} variant="outline" className="text-xs text-orange-400 border-orange-500/30 bg-orange-500/10">
          {f}
        </Badge>
      ))}
    </div>
  )
}

export function SignalsTable({ signals }: { signals: Signal[] }) {
  if (!signals.length) {
    return (
      <div className="text-zinc-500 text-sm p-6 text-center">
        No signals yet. Run the pipeline to generate signals.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="border-zinc-800 hover:bg-transparent">
            <TableHead className="text-zinc-400 font-mono text-xs">ASSET</TableHead>
            <TableHead className="text-zinc-400 font-mono text-xs">SCORE</TableHead>
            <TableHead className="text-zinc-400 font-mono text-xs">CAUSAL PATH</TableHead>
            <TableHead className="text-zinc-400 font-mono text-xs">LAG</TableHead>
            <TableHead className="text-zinc-400 font-mono text-xs">TYPE</TableHead>
            <TableHead className="text-zinc-400 font-mono text-xs">RISKS</TableHead>
            <TableHead className="text-zinc-400 font-mono text-xs">CONF</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {signals.map(s => (
            <TableRow key={s.id} className="border-zinc-800/50 hover:bg-zinc-900/50">
              <TableCell className="font-mono font-bold text-zinc-100 text-sm">
                {s.asset}
              </TableCell>
              <TableCell>
                <ScoreBadge score={s.adjusted_score} />
              </TableCell>
              <TableCell className="text-zinc-400 text-xs font-mono max-w-xs truncate" title={s.why_path}>
                {s.why_path}
              </TableCell>
              <TableCell className="text-zinc-300 text-xs font-mono whitespace-nowrap">
                {s.when_months}mo
              </TableCell>
              <TableCell className="text-xs">
                <Badge variant="outline" className="text-zinc-400 border-zinc-700 text-xs font-mono">
                  {s.event_type?.replace(/_/g, ' ') || '—'}
                </Badge>
              </TableCell>
              <TableCell>
                <RiskFlags flagsJson={s.risk_flags_json} />
              </TableCell>
              <TableCell>
                <span className={`text-xs ${s.confirmed ? 'text-emerald-400' : 'text-zinc-600'}`}>
                  {s.confirmed ? '✓' : '○'}
                </span>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
