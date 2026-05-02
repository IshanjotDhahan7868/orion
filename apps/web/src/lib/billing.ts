import Stripe from 'stripe'

export type PlanKey = 'free' | 'pilot' | 'desk'

export interface SubscriptionPlan {
  key: PlanKey
  name: string
  priceLabel: string
  priceId?: string
  description: string
  headline: string
  features: string[]
}

export const subscriptionPlans: SubscriptionPlan[] = [
  {
    key: 'free',
    name: 'Observer',
    priceLabel: '$0',
    description: 'For evaluation and internal demos.',
    headline: 'See the signal stack and proof surfaces.',
    features: [
      'Read-only dashboard access',
      'Proof metrics and brief archive',
      'No billing required',
    ],
  },
  {
    key: 'pilot',
    name: 'ORION Pilot',
    priceLabel: '$3k-$10k / mo',
    priceId: process.env.STRIPE_PRICE_ORION_PILOT,
    description: 'High-touch research terminal for a single investment team.',
    headline: 'Best first paid offer for serious macro buyers.',
    features: [
      'Dashboard, proof page, and alert routing',
      'Buyer-specific workspace setup',
      'Weekly onboarding and signal review',
    ],
  },
  {
    key: 'desk',
    name: 'ORION Desk',
    priceLabel: '$15k+ / mo',
    priceId: process.env.STRIPE_PRICE_ORION_DESK,
    description: 'Multi-user workflow for institutional macro desks.',
    headline: 'For teams that need alerts, governance, and billing controls.',
    features: [
      'Everything in Pilot',
      'Multi-destination alerting',
      'Billing portal and team workflow support',
    ],
  },
]

export function getPlanByKey(planKey: string | null | undefined): SubscriptionPlan {
  return subscriptionPlans.find(plan => plan.key === planKey) ?? subscriptionPlans[0]
}

export function findPlanByPriceId(priceId: string | null | undefined): SubscriptionPlan | null {
  if (!priceId) return null
  return subscriptionPlans.find(plan => plan.priceId === priceId) ?? null
}

export function getBaseUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_APP_URL
  if (explicit) return explicit.replace(/\/$/, '')
  const vercel = process.env.VERCEL_URL
  if (vercel) return `https://${vercel}`
  return 'http://localhost:3000'
}

export function getStripeServer(): Stripe | null {
  const secretKey = process.env.STRIPE_SECRET_KEY
  if (!secretKey) return null
  return new Stripe(secretKey)
}
