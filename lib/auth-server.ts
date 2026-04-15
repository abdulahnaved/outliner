import { cookies } from 'next/headers'
import { SESSION_COOKIE_NAME, verifyUserSession } from '@/lib/session-token'

export type CurrentUser = { id: number; email: string }

/**
 * Resolved user from cookie: valid JWT.
 *
 * Note: we intentionally avoid a DB roundtrip for every page load/navbar refresh,
 * because serverless Postgres connection setup can dominate latency on Vercel.
 */
export async function getCurrentUser(): Promise<CurrentUser | null> {
  const token = cookies().get(SESSION_COOKIE_NAME)?.value
  if (!token) return null
  const session = await verifyUserSession(token)
  if (!session) return null
  return { id: session.id, email: session.email }
}

export async function getSessionUserId(): Promise<number | null> {
  const user = await getCurrentUser()
  return user?.id ?? null
}

export { SESSION_COOKIE_NAME }
