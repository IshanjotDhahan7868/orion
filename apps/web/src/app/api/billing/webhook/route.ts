import Stripe from 'stripe'

import { findPlanByPriceId, getStripeServer } from '@/lib/billing'
import { updateAccountBilling } from '@/lib/db'

export const runtime = 'nodejs'

function getWebhookSecret(): string | null {
  return process.env.STRIPE_WEBHOOK_SECRET ?? null
}

function extractSubscriptionPriceId(subscription: Stripe.Subscription): string | null {
  const firstItem = subscription.items.data[0]
  return firstItem?.price?.id ?? null
}

export async function POST(req: Request) {
  const stripe = getStripeServer()
  const webhookSecret = getWebhookSecret()
  if (!stripe || !webhookSecret) {
    return new Response('Stripe webhook not configured', { status: 503 })
  }

  const signature = req.headers.get('stripe-signature')
  if (!signature) {
    return new Response('Missing stripe signature', { status: 400 })
  }

  const body = await req.text()

  let event: Stripe.Event
  try {
    event = stripe.webhooks.constructEvent(body, signature, webhookSecret)
  } catch (error) {
    return new Response(`Webhook Error: ${error instanceof Error ? error.message : 'invalid signature'}`, {
      status: 400,
    })
  }

  if (event.type === 'checkout.session.completed') {
    const session = event.data.object as Stripe.Checkout.Session
    const clerkUserId = session.metadata?.clerk_user_id || session.client_reference_id
    if (clerkUserId) {
      const plan = findPlanByPriceId(session.metadata?.price_id)
      await updateAccountBilling({
        clerk_user_id: clerkUserId,
        stripe_customer_id: typeof session.customer === 'string' ? session.customer : session.customer?.id,
        subscription_status: session.payment_status === 'paid' ? 'active' : 'pending',
        plan_key: session.metadata?.plan_key ?? plan?.key ?? 'pilot',
      })
    }
  }

  if (event.type === 'customer.subscription.created' || event.type === 'customer.subscription.updated') {
    const subscription = event.data.object as Stripe.Subscription
    const clerkUserId = subscription.metadata?.clerk_user_id
    if (clerkUserId) {
      const priceId = extractSubscriptionPriceId(subscription)
      const plan = findPlanByPriceId(priceId)
      await updateAccountBilling({
        clerk_user_id: clerkUserId,
        stripe_customer_id: typeof subscription.customer === 'string' ? subscription.customer : subscription.customer.id,
        stripe_subscription_id: subscription.id,
        stripe_price_id: priceId,
        stripe_product_name: plan?.name ?? null,
        subscription_status: subscription.status,
        plan_key: subscription.metadata?.plan_key ?? plan?.key ?? 'pilot',
      })
    }
  }

  if (event.type === 'customer.subscription.deleted') {
    const subscription = event.data.object as Stripe.Subscription
    const clerkUserId = subscription.metadata?.clerk_user_id
    if (clerkUserId) {
      await updateAccountBilling({
        clerk_user_id: clerkUserId,
        stripe_subscription_id: subscription.id,
        stripe_price_id: null,
        stripe_product_name: null,
        subscription_status: 'canceled',
        plan_key: 'free',
      })
    }
  }

  return new Response('ok')
}
