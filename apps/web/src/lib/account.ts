import { currentUser } from '@clerk/nextjs/server'

import { getAccountProfile, type AccountProfile } from '@/lib/db'

export interface ActiveAccountContext {
  clerkUserId: string
  email: string | undefined
  fullName: string | undefined
  profile: AccountProfile
}

export async function getActiveAccountContext(): Promise<ActiveAccountContext | null> {
  const user = await currentUser()
  if (!user) return null

  const email = user.emailAddresses[0]?.emailAddress
  const fullName = [user.firstName, user.lastName].filter(Boolean).join(' ') || user.username || undefined
  const profile =
    (await getAccountProfile(user.id, email, fullName).catch(() => null)) ?? {
      clerk_user_id: user.id,
      email,
      full_name: fullName,
      buyer_type: 'hedge_fund',
      organization_name: '',
      onboarding_notes: '',
      subscription_status: 'inactive',
      plan_key: 'free',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

  return {
    clerkUserId: user.id,
    email,
    fullName,
    profile,
  }
}
