import { auth } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'

export const runtime = 'nodejs'

function getEngineUrl(): string {
  return process.env.ORION_ENGINE_URL || 'http://localhost:8000'
}

export async function POST() {
  const { userId } = await auth()
  if (!userId) {
    return NextResponse.redirect(new URL('/sign-in', process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'))
  }

  try {
    const res = await fetch(`${getEngineUrl()}/api/alerts/test?clerk_user_id=${encodeURIComponent(userId)}`, {
      method: 'POST',
      cache: 'no-store',
    })
    const payload = await res.json()
    return NextResponse.redirect(
      new URL(`/alerts?sent=${payload.deliveries?.length ? '1' : '0'}`, process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000')
    )
  } catch {
    return NextResponse.redirect(new URL('/alerts?sent=0', process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'))
  }
}
