import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { SESSION_COOKIE_NAME, verifyUserSession } from '@/lib/session-token'
import { dbQueryOne } from '@/lib/db'

export const runtime = 'nodejs'

function msSince(t: bigint) {
  return Number((process.hrtime.bigint() - t) / 1_000_000n)
}

export async function GET() {
  const start = process.hrtime.bigint()
  const token = cookies().get(SESSION_COOKIE_NAME)?.value ?? null

  const t1 = process.hrtime.bigint()
  const session = token ? await verifyUserSession(token) : null
  const jwtMs = msSince(t1)

  let dbOk = false
  let dbMs: number | null = null
  try {
    const t2 = process.hrtime.bigint()
    await dbQueryOne('SELECT 1 as ok')
    dbMs = msSince(t2)
    dbOk = true
  } catch {
    dbOk = false
  }

  return NextResponse.json({
    ok: true,
    hasCookie: !!token,
    sessionPresent: !!session,
    jwtMs,
    dbOk,
    dbMs,
    totalMs: msSince(start)
  })
}

