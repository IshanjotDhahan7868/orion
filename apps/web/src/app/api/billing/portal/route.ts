import { auth } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'

import { getBaseUrl, getStripeServer } from '@/lib/billing'
import { getAccountProfile } from '@/lib/db'

export const runtime = 'nodejs'

export async function POST() {
  const { userId } = await auth()
  if (!userId) {
    return NextResponse.redirect(new URL('/sign-in', getBaseUrl()))
  }

  const stripe = getStripeServer()
  if (!stripe) {
    return NextResponse.redirect(new URL('/account?portal=unavailable', getBaseUrl()))
  }

  const profile = await getAccountProfile(userId)
  if (!profile?.stripe_customer_id) {
    return NextResponse.redirect(new URL('/account?portal=unavailable', getBaseUrl()))
  }

  const session = await stripe.billingPortal.sessions.create({
    customer: profile.stripe_customer_id,
    return_url: `${getBaseUrl()}/account`,
  })

  return NextResponse.redirect(session.url)
}
