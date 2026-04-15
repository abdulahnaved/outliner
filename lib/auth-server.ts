import { cookies } from 'next/headers'
import { dbQueryOne } from '@/lib/db'
import { SESSION_COOKIE_NAME, verifyUserSession } from '@/lib/session-token'

export type CurrentUser = { id: number; email: string }

/**
 * Resolved user from cookie: valid JWT **and** row still present in `users`
 * (covers deleted users and stale sessions).
 */
export async function getCurrentUser(): Promise<CurrentUser | null> {
  const token = cookies().get(SESSION_COOKIE_NAME)?.value
  if (!token) return null
  const jwtUserId = await verifyUserSession(token)
  if (jwtUserId === null) return null
  const row = await dbQueryOne<{ id: unknown; email: unknown }>(
    'SELECT id, email FROM users WHERE id = $1',
    [jwtUserId]
  )
  if (!row) return null
  const idRaw = (row as any).id
  const id = typeof idRaw === 'number' ? idRaw : typeof idRaw === 'string' ? Number(idRaw) : NaN
  const email = (row as any).email
  if (!Number.isFinite(id) || typeof email !== 'string') return null
  return { id: Math.trunc(id), email }
}

export async function getSessionUserId(): Promise<number | null> {
  const user = await getCurrentUser()
  return user?.id ?? null
}

export { SESSION_COOKIE_NAME }
