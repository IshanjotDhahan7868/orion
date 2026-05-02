import { redirect } from 'next/navigation'

import { saveWorkspaceProfileAction } from '@/app/actions'
import { AppShell } from '@/components/app-shell'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { getActiveAccountContext } from '@/lib/account'
import { getPlanByKey, subscriptionPlans } from '@/lib/billing'

export default async function AccountPage() {
  const account = await getActiveAccountContext()
  if (!account) redirect('/sign-in')

  const currentPlan = getPlanByKey(account.profile.plan_key)

  return (
    <AppShell
      currentPath="/account"
      title="Account And Billing"
      subtitle="Control how ORION is packaged, billed, and explained to customers."
      planLabel={currentPlan.name}
      buyerType={account.profile.buyer_type}
    >
      <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-6">
          <Card className="border-white/10 bg-white/5 p-5">
            <p className="text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">Current Account</p>
            <div className="mt-4 space-y-3 text-sm text-zinc-300">
              <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-3">
                <span>User</span>
                <span className="font-mono text-white">{account.fullName ?? account.email ?? account.clerkUserId}</span>
              </div>
              <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-3">
                <span>Plan</span>
                <Badge variant="outline" className="border-cyan-400/30 bg-cyan-400/10 text-cyan-200">
                  {currentPlan.name}
                </Badge>
              </div>
              <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-3">
                <span>Subscription status</span>
                <span className="font-mono text-white">{account.profile.subscription_status}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span>Buyer motion</span>
                <span className="font-mono text-white">{account.profile.buyer_type.replace(/_/g, ' ')}</span>
              </div>
            </div>

            <div className="mt-5 flex flex-wrap gap-3">
              <form action="/api/billing/portal" method="post">
                <button type="submit" className="rounded-xl border border-white/10 bg-black/20 px-4 py-2 text-sm text-zinc-200 hover:bg-white/10">
                  Open billing portal
                </button>
              </form>
            </div>
          </Card>

          <Card className="border-white/10 bg-white/5 p-5">
            <p className="text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">Commercial Setup</p>
            <form action={saveWorkspaceProfileAction} className="mt-4 space-y-4">
              <div>
                <label className="text-xs font-mono uppercase tracking-[0.2em] text-zinc-500">Organization</label>
                <input
                  name="organization_name"
                  defaultValue={account.profile.organization_name ?? ''}
                  className="mt-2 w-full rounded-xl border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                />
              </div>
              <div>
                <label className="text-xs font-mono uppercase tracking-[0.2em] text-zinc-500">Buyer Type</label>
                <select
                  name="buyer_type"
                  defaultValue={account.profile.buyer_type}
                  className="mt-2 w-full rounded-xl border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                >
                  <option value="hedge_fund">Hedge Fund PM</option>
                  <option value="family_office">Family Office CIO</option>
                  <option value="ria">RIA / Advisor</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-mono uppercase tracking-[0.2em] text-zinc-500">Onboarding Notes</label>
                <textarea
                  name="onboarding_notes"
                  defaultValue={account.profile.onboarding_notes ?? ''}
                  className="mt-2 min-h-28 w-full rounded-xl border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                />
              </div>
              <button type="submit" className="rounded-xl bg-cyan-300 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-cyan-200">
                Save account profile
              </button>
            </form>
          </Card>
        </div>

        <Card className="border-white/10 bg-white/5 p-5">
          <p className="text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">Plans</p>
          <div className="mt-4 space-y-4">
            {subscriptionPlans.map(plan => {
              const active = plan.key === currentPlan.key
              return (
                <div key={plan.key} className={`rounded-2xl border p-4 ${active ? 'border-cyan-400/30 bg-cyan-400/10' : 'border-white/10 bg-black/20'}`}>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-lg font-semibold text-white">{plan.name}</p>
                      <p className="mt-1 text-sm text-zinc-400">{plan.description}</p>
                    </div>
                    <p className="font-mono text-lg text-cyan-200">{plan.priceLabel}</p>
                  </div>
                  <p className="mt-3 text-sm text-zinc-300">{plan.headline}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {plan.features.map(feature => (
                      <Badge key={feature} variant="outline" className="border-white/10 bg-white/5 text-zinc-200">
                        {feature}
                      </Badge>
                    ))}
                  </div>
                  <div className="mt-4">
                    {plan.key === 'free' ? (
                      <span className="text-sm text-zinc-500">Included for local evaluation.</span>
                    ) : (
                      <form action="/api/billing/checkout" method="post">
                        <input type="hidden" name="plan" value={plan.key} />
                        <button
                          type="submit"
                          disabled={!plan.priceId}
                          className="rounded-xl bg-cyan-300 px-4 py-2 text-sm font-medium text-zinc-950 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {active ? 'Change plan in Stripe' : `Choose ${plan.name}`}
                        </button>
                      </form>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      </div>
    </AppShell>
  )
}
