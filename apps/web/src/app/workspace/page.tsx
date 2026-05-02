import { redirect } from 'next/navigation'

import { saveWorkspaceProfileAction } from '@/app/actions'
import { AppShell } from '@/components/app-shell'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { getActiveAccountContext } from '@/lib/account'
import { getPlanByKey } from '@/lib/billing'

const buyerModes = [
  {
    key: 'hedge_fund',
    label: 'Hedge Fund PM',
    focus: 'Concentrated trade ideas, regime change detection, and explainable timing.',
  },
  {
    key: 'family_office',
    label: 'Family Office CIO',
    focus: 'Longer-horizon portfolio tilts, concentration control, and macro risk awareness.',
  },
  {
    key: 'ria',
    label: 'RIA / Advisor',
    focus: 'Client-safe briefings, thematic portfolio explanations, and watchlist monitoring.',
  },
]

export default async function WorkspacePage() {
  const account = await getActiveAccountContext()
  if (!account) redirect('/sign-in')

  const plan = getPlanByKey(account.profile.plan_key)

  return (
    <AppShell
      currentPath="/workspace"
      title="Buyer-Specific Workspace"
      subtitle="Configure ORION around the buyer workflow you actually want to sell."
      planLabel={plan.name}
      buyerType={account.profile.buyer_type}
    >
      <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-white/10 bg-white/5 p-5">
          <p className="text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">Workflow Positioning</p>
          <h2 className="mt-3 text-2xl font-semibold text-white">Stop selling a generic AI terminal.</h2>
          <p className="mt-3 text-sm leading-6 text-zinc-300">
            Choose the buyer ORION is serving, then shape the briefs, alerts, and demo narrative around that outcome.
          </p>

          <div className="mt-5 grid gap-3">
            {buyerModes.map(mode => {
              const active = account.profile.buyer_type === mode.key
              return (
                <div
                  key={mode.key}
                  className={`rounded-2xl border p-4 ${active ? 'border-cyan-400/30 bg-cyan-400/10' : 'border-white/10 bg-black/20'}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-base font-semibold text-white">{mode.label}</p>
                    {active ? (
                      <Badge variant="outline" className="border-cyan-400/30 bg-cyan-400/10 text-cyan-200">
                        active
                      </Badge>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-zinc-300">{mode.focus}</p>
                </div>
              )
            })}
          </div>
        </Card>

        <Card className="border-white/10 bg-white/5 p-5">
          <p className="text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">Account Setup</p>
          <form action={saveWorkspaceProfileAction} className="mt-4 space-y-4">
            <div>
              <label className="text-xs font-mono uppercase tracking-[0.2em] text-zinc-500">Buyer Type</label>
              <select
                name="buyer_type"
                defaultValue={account.profile.buyer_type}
                className="mt-2 w-full rounded-xl border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
              >
                {buyerModes.map(mode => (
                  <option key={mode.key} value={mode.key}>
                    {mode.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-mono uppercase tracking-[0.2em] text-zinc-500">Organization</label>
              <input
                name="organization_name"
                defaultValue={account.profile.organization_name ?? ''}
                className="mt-2 w-full rounded-xl border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                placeholder="North Star Capital"
              />
            </div>

            <div>
              <label className="text-xs font-mono uppercase tracking-[0.2em] text-zinc-500">Onboarding Notes</label>
              <textarea
                name="onboarding_notes"
                defaultValue={account.profile.onboarding_notes ?? ''}
                className="mt-2 min-h-32 w-full rounded-xl border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                placeholder="Mandate, themes, concentration limits, client reporting style..."
              />
            </div>

            <button
              type="submit"
              className="rounded-xl bg-cyan-300 px-4 py-2 text-sm font-medium text-zinc-950 transition hover:bg-cyan-200"
            >
              Save workspace profile
            </button>
          </form>
        </Card>
      </div>
    </AppShell>
  )
}
