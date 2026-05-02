import { auth, currentUser } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'

import { getBaseUrl, getPlanByKey, getStripeServer } from '@/lib/billing'
import { getAccountProfile, saveAccountProfile, updateAccountBilling } from '@/lib/db'

export const runtime = 'nodejs'

export async function POST(req: Request) {
  const { userId } = await auth()
  if (!userId) {
    return NextResponse.redirect(new URL('/sign-in', getBaseUrl()))
  }

  const formData = await req.formData()
  const planKey = String(formData.get('plan') || 'pilot')
  const plan = getPlanByKey(planKey)
  const stripe = getStripeServer()

  if (!stripe || !plan.priceId) {
    return NextResponse.redirect(new URL('/account?billing=unavailable', getBaseUrl()))
  }

  const user = await currentUser()
  const email = user?.emailAddresses[0]?.emailAddress
  const fullName = [user?.firstName, user?.lastName].filter(Boolean).join(' ') || user?.username || undefined
  const profile = await getAccountProfile(userId, email, fullName)

  let stripeCustomerId = profile?.stripe_customer_id ?? null
  if (!stripeCustomerId) {
    const customer = await stripe.customers.create({
      email,
      name: fullName,
      metadata: {
        clerk_user_id: userId,
      },
    })
    stripeCustomerId = customer.id
    await saveAccountProfile({
      clerk_user_id: userId,
      email,
      full_name: fullName,
      buyer_type: profile?.buyer_type ?? 'hedge_fund',
      organization_name: profile?.organization_name ?? '',
      onboarding_notes: profile?.onboarding_notes ?? '',
    })
    await updateAccountBilling({
      clerk_user_id: userId,
      stripe_customer_id: stripeCustomerId,
      subscription_status: profile?.subscription_status ?? 'inactive',
      plan_key: profile?.plan_key ?? 'free',
    })
  }

  const session = await stripe.checkout.sessions.create({
    mode: 'subscription',
    customer: stripeCustomerId,
    line_items: [{ price: plan.priceId, quantity: 1 }],
    success_url: `${getBaseUrl()}/account?checkout=success`,
    cancel_url: `${getBaseUrl()}/account?checkout=cancelled`,
    allow_promotion_codes: true,
    client_reference_id: userId,
    metadata: {
      clerk_user_id: userId,
      plan_key: plan.key,
      price_id: plan.priceId,
    },
    subscription_data: {
      metadata: {
        clerk_user_id: userId,
        plan_key: plan.key,
      },
    },
  })

  if (!session.url) {
    return NextResponse.redirect(new URL('/account?checkout=failed', getBaseUrl()))
  }

  return NextResponse.redirect(session.url)
}
