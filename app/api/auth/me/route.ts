import { NextResponse } from 'next/server'
import { getCurrentUser } from '@/lib/auth-server'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const noStore = {
  'Cache-Control': 'private, no-store, must-revalidate'
} as const

export async function GET() {
  let user = null
  try {
    user = await getCurrentUser()
  } catch {
    // If the DB/env is misconfigured, treat as logged out instead of 500'ing.
    // This keeps the navbar stable and avoids noisy dev logs.
    user = null
  }
  if (!user) {
    return NextResponse.json({ user: null }, { headers: noStore })
  }
  // Ensure numeric id for client UI (pg BIGINT can arrive as string if unnormalized).
  return NextResponse.json(
    { user: { id: Number(user.id), email: user.email } },
    { headers: noStore }
  )
}
