'use server'

import { auth, currentUser } from '@clerk/nextjs/server'
import { revalidatePath } from 'next/cache'

import { createAlert, saveAccountProfile } from '@/lib/db'

export async function saveWorkspaceProfileAction(formData: FormData) {
  const { userId } = await auth()
  if (!userId) {
    throw new Error('Unauthorized')
  }

  const user = await currentUser()
  const email = user?.emailAddresses[0]?.emailAddress ?? null
  const fullName =
    [user?.firstName, user?.lastName].filter(Boolean).join(' ') || user?.username || null

  await saveAccountProfile({
    clerk_user_id: userId,
    email,
    full_name: fullName,
    buyer_type: String(formData.get('buyer_type') || 'hedge_fund'),
    organization_name: String(formData.get('organization_name') || ''),
    onboarding_notes: String(formData.get('onboarding_notes') || ''),
  })

  revalidatePath('/workspace')
  revalidatePath('/account')
  revalidatePath('/dashboard')
  revalidatePath('/proof')
}

export async function createAlertAction(formData: FormData) {
  const { userId } = await auth()
  if (!userId) {
    throw new Error('Unauthorized')
  }

  await createAlert({
    clerk_user_id: userId,
    label: String(formData.get('label') || 'ORION alert'),
    channel: String(formData.get('channel') || 'email'),
    destination: String(formData.get('destination') || ''),
    min_score: Number(formData.get('min_score') || 0.7),
    confirmed_only: formData.get('confirmed_only') === 'on',
  })

  revalidatePath('/alerts')
}
