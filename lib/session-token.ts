import { SignJWT, jwtVerify } from 'jose'

export const SESSION_COOKIE_NAME = 'outliner_session'

const DEV_FALLBACK = 'dev-outliner-secret-min-32-chars!!'

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

export async function signUserSession(userId: number): Promise<string> {
  return new SignJWT({})
    .setProtectedHeader({ alg: 'HS256' })
    .setSubject(String(userId))
    .setIssuedAt()
    .setExpirationTime('7d')
    .sign(getAuthSecretKey())
}

export async function verifyUserSession(token: string): Promise<number | null> {
  try {
    const { payload } = await jwtVerify(token, getAuthSecretKey())
    const sub = payload.sub
    if (typeof sub === 'string' && /^\d+$/.test(sub)) {
      return parseInt(sub, 10)
    }
    return null
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
