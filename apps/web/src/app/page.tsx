import Link from 'next/link'

import { Badge } from '@/components/ui/badge'
import { buttonVariants } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { getLatestSignals, getLatestPortfolioSnapshot, getWatchlists } from '@/lib/db'
import { cn } from '@/lib/utils'

export const dynamic = 'force-dynamic'

function formatPct(value: number) {
  return `${(value * 100).toFixed(1)}%`
}

export default async function HomePage() {
  const [signals, portfolio, watchlists] = await Promise.all([
    getLatestSignals(25).catch(() => []),
    getLatestPortfolioSnapshot().catch(() => null),
    getWatchlists().catch(() => []),
  ])

  const confirmedSignals = signals.filter(signal => signal.confirmed)
  const topSignal = signals[0] ?? null
  const avgTopScore =
    signals.length > 0
      ? signals.slice(0, 10).reduce((sum, signal) => sum + signal.adjusted_score, 0) / Math.min(signals.length, 10)
      : 0
  const averagePositionWeight =
    portfolio?.positions.length
      ? portfolio.positions.reduce((sum, position) => sum + position.weight, 0) / portfolio.positions.length
      : 0

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.16),transparent_32%),linear-gradient(180deg,#09090b_0%,#09090b_45%,#111827_100%)] text-zinc-100">
      <section className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-6 py-8 lg:px-10">
        <header className="flex items-center justify-between gap-4 border-b border-white/10 pb-6">
          <div className="flex items-center gap-3">
            <span className="text-xl text-cyan-300">⬡</span>
            <div>
              <p className="font-mono text-sm tracking-[0.35em] text-zinc-300">ORION</p>
              <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">Causal Macro Intelligence</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/dashboard"
              className={cn(
                buttonVariants({ variant: 'outline' }),
                'border-white/15 bg-white/5 text-zinc-100 hover:bg-white/10'
              )}
            >
              Open Live Terminal
            </Link>
          </div>
        </header>

        <div className="grid flex-1 gap-10 py-10 lg:grid-cols-[1.35fr_0.9fr] lg:items-center">
          <div className="space-y-7">
            <Badge variant="outline" className="border-emerald-400/30 bg-emerald-400/10 font-mono text-emerald-200">
              Built to sell outcomes, not dashboards
            </Badge>

            <div className="space-y-5">
              <h1 className="max-w-4xl text-5xl font-semibold tracking-tight text-white sm:text-6xl">
                Turn macro chaos into concentrated, explainable trade ideas that people will pay for.
              </h1>
              <p className="max-w-3xl text-lg leading-8 text-zinc-300">
                ORION already has the beginnings of a real signal engine: causal graph mapping, event parsing,
                propagation, market confirmation, portfolio sizing, and an analyst chat surface. The next money step
                is not “more AI.” It is proving value fast, packaging the workflow cleanly, and making the product
                look like it can move capital with discipline.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <Card className="border-white/10 bg-white/5 p-4">
                <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-zinc-500">Live Signals</p>
                <p className="mt-3 text-3xl font-semibold text-white">{signals.length}</p>
                <p className="mt-1 text-sm text-zinc-400">
                  {confirmedSignals.length} confirmed by market filters
                </p>
              </Card>
              <Card className="border-white/10 bg-white/5 p-4">
                <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-zinc-500">Top 10 Avg Score</p>
                <p className="mt-3 text-3xl font-semibold text-white">{avgTopScore.toFixed(2)}</p>
                <p className="mt-1 text-sm text-zinc-400">
                  Current signal stack quality indicator
                </p>
              </Card>
              <Card className="border-white/10 bg-white/5 p-4">
                <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-zinc-500">Portfolio Snapshot</p>
                <p className="mt-3 text-3xl font-semibold text-white">
                  {portfolio ? formatPct(portfolio.summary.gross_exposure) : '0.0%'}
                </p>
                <p className="mt-1 text-sm text-zinc-400">
                  {portfolio ? `${portfolio.positions.length} positions sized` : 'No saved allocation yet'}
                </p>
              </Card>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link
                href="/dashboard"
                className={cn(buttonVariants(), 'bg-cyan-300 text-zinc-950 hover:bg-cyan-200')}
              >
                See The Product
              </Link>
              <Link
                href="/dashboard"
                className={cn(
                  buttonVariants({ variant: 'outline' }),
                  'border-white/15 bg-white/5 text-zinc-100 hover:bg-white/10'
                )}
              >
                Run The Investor Demo
              </Link>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <Card className="border-amber-400/20 bg-amber-400/8 p-4">
                <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-amber-200">What Sells First</p>
                <p className="mt-2 text-sm leading-6 text-zinc-300">
                  A high-ticket research terminal or pilot, not commodity self-serve SaaS.
                </p>
              </Card>
              <Card className="border-cyan-400/20 bg-cyan-400/8 p-4">
                <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-cyan-200">Value Story</p>
                <p className="mt-2 text-sm leading-6 text-zinc-300">
                  “We explain why capital should move, before the move is obvious.”
                </p>
              </Card>
              <Card className="border-rose-400/20 bg-rose-400/8 p-4">
                <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-rose-200">Current Blocker</p>
                <p className="mt-2 text-sm leading-6 text-zinc-300">
                  No real auth, billing, tenanting, or customer-safe proof loop yet.
                </p>
              </Card>
            </div>
          </div>

          <div className="space-y-4">
            <Card className="overflow-hidden border-white/10 bg-zinc-950/80 shadow-2xl shadow-cyan-950/30">
              <div className="border-b border-white/10 px-5 py-4">
                <p className="font-mono text-xs uppercase tracking-[0.3em] text-zinc-500">Commercial Readiness</p>
                <p className="mt-2 text-xl font-semibold text-white">Alpha-quality demo, not self-serve SaaS</p>
              </div>
              <div className="space-y-5 px-5 py-5 text-sm text-zinc-300">
                <div>
                  <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-zinc-500">Works Today</p>
                  <p className="mt-2 leading-6">
                    Signal generation, graph explainability, portfolio recommendation, and a presentable analyst UI are
                    already there.
                  </p>
                </div>
                <div>
                  <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-zinc-500">Can Make Money Soon</p>
                  <p className="mt-2 leading-6">
                    Sell a pilot with manual onboarding, white-glove research delivery, and one buyer segment that
                    cares about regime shifts.
                  </p>
                </div>
                <div>
                  <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-zinc-500">Not Ready For</p>
                  <p className="mt-2 leading-6">
                    Broad self-serve subscriptions, compliance-sensitive customers, or promises of systematic alpha at
                    scale.
                  </p>
                </div>
              </div>
            </Card>

            <Card className="border-white/10 bg-white/5 p-5">
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-zinc-500">Best Initial Offer</p>
              <div className="mt-4 space-y-4">
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-lg font-semibold text-white">ORION Pilot</p>
                      <p className="text-sm text-zinc-400">For hedge funds, family offices, macro PMs</p>
                    </div>
                    <p className="font-mono text-lg text-cyan-300">$3k-$10k/mo</p>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-zinc-300">
                    Daily brief, watchlist intelligence, top signal review, and analyst chat. Sell the workflow, not
                    just the raw model.
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-lg font-semibold text-white">ORION Desk</p>
                      <p className="text-sm text-zinc-400">Once auth, billing, and delivery are real</p>
                    </div>
                    <p className="font-mono text-lg text-emerald-300">$15k+/mo</p>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-zinc-300">
                    Multi-user workspace, alerts, saved scenarios, allocation governance, and evidence-backed signal
                    packets.
                  </p>
                </div>
              </div>
            </Card>

            <Card className="border-white/10 bg-white/5 p-5">
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-zinc-500">Current Product Surface</p>
              <div className="mt-4 space-y-3 text-sm text-zinc-300">
                <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-3">
                  <span>Top live signal</span>
                  <span className="font-mono text-white">
                    {topSignal ? `${topSignal.asset} ${topSignal.adjusted_score.toFixed(2)}` : 'No live signal'}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-3">
                  <span>Saved watchlists</span>
                  <span className="font-mono text-white">{watchlists.length}</span>
                </div>
                <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-3">
                  <span>Avg position weight</span>
                  <span className="font-mono text-white">{formatPct(averagePositionWeight)}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>Primary value narrative</span>
                  <span className="font-mono text-right text-cyan-200">Why this asset, why now, why before consensus</span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </section>
    </main>
  )
}
