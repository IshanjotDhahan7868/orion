import { redirect } from 'next/navigation'

import { createAlertAction } from '@/app/actions'
import { AppShell } from '@/components/app-shell'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { getActiveAccountContext } from '@/lib/account'
import { getPlanByKey } from '@/lib/billing'
import { getAlerts } from '@/lib/db'

export default async function AlertsPage() {
  const account = await getActiveAccountContext()
  if (!account) redirect('/sign-in')

  const [alerts] = await Promise.all([getAlerts(account.clerkUserId).catch(() => [])])
  const plan = getPlanByKey(account.profile.plan_key)

  return (
    <AppShell
      currentPath="/alerts"
      title="Alert Delivery"
      subtitle="Push ORION into inboxes and webhooks so customers feel the product working between logins."
      planLabel={plan.name}
      buyerType={account.profile.buyer_type}
    >
      <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
        <Card className="border-white/10 bg-white/5 p-5">
          <p className="text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">Create Alert Destination</p>
          <form action={createAlertAction} className="mt-4 space-y-4">
            <div>
              <label className="text-xs font-mono uppercase tracking-[0.2em] text-zinc-500">Label</label>
              <input
                name="label"
                defaultValue={`${account.profile.buyer_type.replace(/_/g, ' ')} daily digest`}
                className="mt-2 w-full rounded-xl border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
              />
            </div>

            <div>
              <label className="text-xs font-mono uppercase tracking-[0.2em] text-zinc-500">Channel</label>
              <select
                name="channel"
                defaultValue="email"
                className="mt-2 w-full rounded-xl border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
              >
                <option value="email">Email via Resend</option>
                <option value="webhook">Generic webhook</option>
                <option value="slack">Slack webhook</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-mono uppercase tracking-[0.2em] text-zinc-500">Destination</label>
              <input
                name="destination"
                defaultValue={account.email ?? ''}
                className="mt-2 w-full rounded-xl border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                placeholder="email@example.com or webhook URL"
              />
            </div>

            <div>
              <label className="text-xs font-mono uppercase tracking-[0.2em] text-zinc-500">Minimum Score</label>
              <input
                type="number"
                name="min_score"
                min="0"
                max="5"
                step="0.05"
                defaultValue="0.75"
                className="mt-2 w-full rounded-xl border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
              />
            </div>

            <label className="flex items-center gap-3 text-sm text-zinc-300">
              <input type="checkbox" name="confirmed_only" defaultChecked className="rounded border-white/10 bg-zinc-950" />
              Only send market-confirmed signals
            </label>

            <button
              type="submit"
              className="rounded-xl bg-cyan-300 px-4 py-2 text-sm font-medium text-zinc-950 transition hover:bg-cyan-200"
            >
              Save alert destination
            </button>
          </form>
        </Card>

        <Card className="border-white/10 bg-white/5 p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">Active Destinations</p>
              <p className="mt-2 text-sm text-zinc-400">These can be triggered by a cron job, webhook, or manual test call.</p>
            </div>
            <form action="/api/alerts/test" method="post">
              <button type="submit" className="rounded-xl border border-white/10 bg-black/20 px-4 py-2 text-sm text-zinc-200 hover:bg-white/10">
                Send test digest
              </button>
            </form>
          </div>

          <div className="mt-5 space-y-3">
            {alerts.length ? (
              alerts.map(alert => (
                <div key={alert.alert_id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-base font-semibold text-white">{alert.label}</p>
                      <p className="mt-1 text-sm text-zinc-400">{alert.destination}</p>
                    </div>
                    <Badge variant="outline" className="border-white/10 bg-white/5 text-zinc-200">
                      {alert.channel}
                    </Badge>
                  </div>
                  <p className="mt-3 text-xs text-zinc-500">
                    min score {alert.min_score.toFixed(2)} · {alert.confirmed_only ? 'confirmed only' : 'all signals'} · last sent {alert.last_sent_at ?? 'never'}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm text-zinc-500">No destinations yet. Create one on the left.</p>
            )}
          </div>
        </Card>
      </div>
    </AppShell>
  )
}
