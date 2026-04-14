import { NextResponse } from 'next/server'
import { verifyPassword } from '@/lib/password'
import { getDb } from '@/lib/db'
import {
  SESSION_COOKIE_NAME,
  sessionCookieOptions,
  signUserSession
} from '@/lib/session-token'

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

  const db = getDb()
  const row = db
    .prepare('SELECT id, email, password_hash FROM users WHERE email = ?')
    .get(email) as { id: number; email: string; password_hash: string } | undefined

  if (!row || !verifyPassword(password, row.password_hash)) {
    return NextResponse.json({ error: 'Invalid email or password' }, { status: 401 })
  }

  const token = await signUserSession(row.id)
  const res = NextResponse.json({ ok: true, user: { id: row.id, email: row.email } })
  res.cookies.set(SESSION_COOKIE_NAME, token, sessionCookieOptions())
  return res
}
