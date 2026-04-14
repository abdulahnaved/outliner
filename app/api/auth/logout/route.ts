import { NextResponse } from 'next/server'
import { SESSION_COOKIE_NAME } from '@/lib/session-token'

export async function POST() {
  const res = NextResponse.json({ ok: true })
  res.cookies.set(SESSION_COOKIE_NAME, '', {
    httpOnly: true,
    sameSite: 'lax',
    path: '/',
    secure: process.env.NODE_ENV === 'production',
    maxAge: 0
  })
  return res
}
