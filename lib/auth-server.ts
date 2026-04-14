import { cookies } from 'next/headers'
import { getDb } from '@/lib/db'
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
  const db = getDb()
  const row = db
    .prepare('SELECT id, email FROM users WHERE id = ?')
    .get(jwtUserId) as CurrentUser | undefined
  return row ?? null
}

export async function getSessionUserId(): Promise<number | null> {
  const user = await getCurrentUser()
  return user?.id ?? null
}

export { SESSION_COOKIE_NAME }
