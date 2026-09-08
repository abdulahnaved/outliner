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
    user = null
  }
  if (!user) {
    return NextResponse.json({ user: null }, { headers: noStore })
  }
    return NextResponse.json(
    { user: { id: Number(user.id), email: user.email } },
    { headers: noStore }
  )
}
