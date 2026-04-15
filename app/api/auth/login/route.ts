import { NextResponse } from 'next/server'
import { verifyPassword } from '@/lib/password'
import { dbQueryOne } from '@/lib/db'
import {
  SESSION_COOKIE_NAME,
  sessionCookieOptions,
  signUserSession
} from '@/lib/session-token'

export const runtime = 'nodejs'

export async function POST(request: Request) {
  let body: unknown
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }
  const o = body as Record<string, unknown>
  const email = typeof o.email === 'string' ? o.email.trim().toLowerCase() : ''
  const password = typeof o.password === 'string' ? o.password : ''

  if (!email || !password) {
    return NextResponse.json({ error: 'Email and password required' }, { status: 400 })
  }

  let row: { id: unknown; email: unknown; password_hash: unknown } | null = null
  try {
    row = await dbQueryOne<{ id: unknown; email: unknown; password_hash: unknown }>(
      'SELECT id, email, password_hash FROM users WHERE email = $1',
      [email]
    )
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : ''
    // Make common Vercel misconfigurations visible to the UI.
    if (msg.includes('DATABASE_URL')) {
      return NextResponse.json(
        { error: 'Server misconfigured: DATABASE_URL not set.' },
        { status: 500 }
      )
    }
    if (msg.toLowerCase().includes('outliner_auth_secret')) {
      return NextResponse.json(
        { error: 'Server misconfigured: OUTLINER_AUTH_SECRET not set.' },
        { status: 500 }
      )
    }
    return NextResponse.json({ error: 'Server error.' }, { status: 500 })
  }

  const idRaw = row ? (row as any).id : undefined
  const id = typeof idRaw === 'number' ? idRaw : typeof idRaw === 'string' ? Number(idRaw) : NaN
  const emailDb = row ? (row as any).email : undefined
  const passwordHash = row ? (row as any).password_hash : undefined

  if (!Number.isFinite(id) || typeof emailDb !== 'string' || typeof passwordHash !== 'string') {
    return NextResponse.json({ error: 'Invalid email or password' }, { status: 401 })
  }

  if (!verifyPassword(password, passwordHash)) {
    return NextResponse.json({ error: 'Invalid email or password' }, { status: 401 })
  }

  const userId = Math.trunc(id)
  const token = await signUserSession({ id: userId, email: emailDb })
  const res = NextResponse.json({ ok: true, user: { id: userId, email: emailDb } })
  res.cookies.set(SESSION_COOKIE_NAME, token, sessionCookieOptions())
  return res
}
