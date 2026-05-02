import { redirect } from 'next/navigation'

import { AppShell } from '@/components/app-shell'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { getActiveAccountContext } from '@/lib/account'
import { getPlanByKey } from '@/lib/billing'
import { getPerformanceSummary } from '@/lib/db'

function formatPct(value: number) {
  return `${(value * 100).toFixed(1)}%`
}

export default async function ProofPage() {
  const account = await getActiveAccountContext()
  if (!account) redirect('/sign-in')

  const [performance] = await Promise.all([getPerformanceSummary().catch(() => null)])
  const plan = getPlanByKey(account.profile.plan_key)

  return (
    <AppShell
      currentPath="/proof"
      title="Proof And Performance"
      subtitle="Show buyers evidence the engine is coherent, filtered, and worth paying for."
      planLabel={plan.name}
      buyerType={account.profile.buyer_type}
    >
      {performance ? (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-4">
            {performance.proof_points.map(point => (
              <Card key={point.label} className="border-white/10 bg-white/5 p-4">
                <p className="text-[11px] font-mono uppercase tracking-[0.24em] text-zinc-500">{point.label}</p>
                <p className="mt-3 text-3xl font-semibold text-white">{point.display}</p>
                <p className="mt-2 text-sm leading-6 text-zinc-400">{point.description}</p>
              </Card>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <Card className="border-white/10 bg-white/5 p-5">
              <p className="text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">Signal History</p>
              <div className="mt-4 space-y-3">
                {performance.signal_history.slice(0, 12).map(signal => (
                  <div key={`${signal.asset}-${signal.created_at}`} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-base font-semibold text-white">{signal.asset}</p>
                        <p className="mt-1 text-xs text-zinc-500">{signal.why_path}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-mono text-lg text-cyan-200">{signal.score.toFixed(2)}</p>
                        <p className="text-xs text-zinc-500">
                          {signal.confirmed ? 'confirmed' : 'unconfirmed'} · {signal.lag_months}mo
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <div className="space-y-6">
              <Card className="border-white/10 bg-white/5 p-5">
                <p className="text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">Theme Exposure</p>
                <div className="mt-4 space-y-3">
                  {Object.entries(performance.theme_exposure).length ? (
                    Object.entries(performance.theme_exposure).map(([theme, value]) => (
                      <div key={theme} className="flex items-center justify-between gap-4 rounded-xl border border-white/10 bg-black/20 px-3 py-2">
                        <span className="text-sm text-zinc-200">{theme}</span>
                        <span className="font-mono text-sm text-cyan-200">{formatPct(value)}</span>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-zinc-500">No portfolio snapshot theme exposure yet.</p>
                  )}
                </div>
              </Card>

              <Card className="border-white/10 bg-white/5 p-5">
                <p className="text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">Brief Archive</p>
                <div className="mt-4 space-y-3">
                  {performance.recent_briefs.length ? (
                    performance.recent_briefs.map(brief => (
                      <div key={brief.brief_id} className="rounded-xl border border-white/10 bg-black/20 px-3 py-3">
                        <p className="text-sm font-semibold text-white">{brief.title}</p>
                        <p className="mt-1 text-xs text-zinc-500">
                          {brief.brief_date} · created {brief.created_at}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-zinc-500">No saved briefs yet.</p>
                  )}
                </div>
              </Card>

              <Card className="border-white/10 bg-white/5 p-5">
                <p className="text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">Most Repeated Causal Nodes</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {performance.event_nodes.map(node => (
                    <Badge key={node.name} variant="outline" className="border-white/10 bg-black/20 text-zinc-200">
                      {node.name} · {node.count}
                    </Badge>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        </div>
      ) : (
        <Card className="border-white/10 bg-white/5 p-5">
          <p className="text-sm text-zinc-400">Performance data is unavailable. Start the engine and refresh the state cache.</p>
        </Card>
      )}
    </AppShell>
  )
}
