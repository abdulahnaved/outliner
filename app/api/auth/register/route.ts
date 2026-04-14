import { NextResponse } from 'next/server'
import { hashPassword } from '@/lib/password'
import { getDb } from '@/lib/db'
import {
  SESSION_COOKIE_NAME,
  sessionCookieOptions,
  signUserSession
} from '@/lib/session-token'

const MAX_EMAIL_LEN = 254
/** bcrypt effectively uses the first 72 bytes; keep a clear cap for users */
const MAX_PASSWORD_LEN = 72

function validEmail(s: string): boolean {
  return s.length <= MAX_EMAIL_LEN && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s)
}

export async function POST(request: Request) {
  let body: unknown
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }
  const o = body as Record<string, unknown>
  const emailRaw = typeof o.email === 'string' ? o.email.trim().toLowerCase() : ''
  const password = typeof o.password === 'string' ? o.password : ''

  if (!emailRaw || !validEmail(emailRaw)) {
    return NextResponse.json({ error: 'Valid email required' }, { status: 400 })
  }
  if (password.length < 8) {
    return NextResponse.json(
      { error: 'Password must be at least 8 characters' },
      { status: 400 }
    )
  }
  if (password.length > MAX_PASSWORD_LEN) {
    return NextResponse.json(
      { error: `Password must be at most ${MAX_PASSWORD_LEN} characters` },
      { status: 400 }
    )
  }

  const passwordHash = hashPassword(password)
  const db = getDb()

  try {
    const r = db
      .prepare('INSERT INTO users (email, password_hash) VALUES (?, ?)')
      .run(emailRaw, passwordHash)
    const userId = Number(r.lastInsertRowid)
    const token = await signUserSession(userId)
    const res = NextResponse.json({ ok: true, user: { id: userId, email: emailRaw } })
    res.cookies.set(SESSION_COOKIE_NAME, token, sessionCookieOptions())
    return res
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : ''
    if (msg.includes('UNIQUE') || msg.includes('unique')) {
      return NextResponse.json({ error: 'Email already registered' }, { status: 409 })
    }
    throw e
  }
}
