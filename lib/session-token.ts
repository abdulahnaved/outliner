import { SignJWT, jwtVerify } from 'jose'

export const SESSION_COOKIE_NAME = 'outliner_session'

const DEV_FALLBACK = 'dev-outliner-secret-min-32-chars!!'

export type SessionUser = { id: number; email: string }

export function getAuthSecretKey(): Uint8Array {
  const s = process.env.OUTLINER_AUTH_SECRET
  if (s && s.length >= 16) {
    return new TextEncoder().encode(s)
  }
  if (process.env.NODE_ENV !== 'production') {
    console.warn('[outliner] OUTLINER_AUTH_SECRET not set; using a dev-only signing key')
    return new TextEncoder().encode(DEV_FALLBACK)
  }
  throw new Error('OUTLINER_AUTH_SECRET must be set (at least 16 characters) in production')
}

export async function signUserSession(user: SessionUser): Promise<string> {
  return new SignJWT({ email: user.email })
    .setProtectedHeader({ alg: 'HS256' })
    .setSubject(String(user.id))
    .setIssuedAt()
    .setExpirationTime('7d')
    .sign(getAuthSecretKey())
}

export async function verifyUserSession(token: string): Promise<SessionUser | null> {
  try {
    const { payload } = await jwtVerify(token, getAuthSecretKey())
    const sub = payload.sub
    const email = (payload as any).email
    if (typeof sub !== 'string' || !/^\d+$/.test(sub)) return null
    if (typeof email !== 'string' || email.length < 3 || email.length > 254) return null
    return { id: parseInt(sub, 10), email }
  } catch {
    return null
  }
}

export function sessionCookieOptions() {
  return {
    httpOnly: true as const,
    sameSite: 'lax' as const,
    path: '/',
    secure: process.env.NODE_ENV === 'production',
    maxAge: 60 * 60 * 24 * 7
  }
}
