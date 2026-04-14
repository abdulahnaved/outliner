import { NextResponse } from 'next/server'
import { getSessionUserId } from '@/lib/auth-server'
import { getDb } from '@/lib/db'

type RouteContext = { params: { id: string } }

export async function GET(_request: Request, context: RouteContext) {
  const userId = await getSessionUserId()
  if (userId === null) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const rawId = context.params.id
  const id = parseInt(rawId, 10)
  if (!Number.isFinite(id) || id < 1) {
    return NextResponse.json({ error: 'Invalid scan id' }, { status: 400 })
  }

  const db = getDb()
  const row = db
    .prepare('SELECT result_json FROM saved_scans WHERE id = ? AND user_id = ?')
    .get(id, userId) as { result_json: string } | undefined

  if (!row) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 })
  }

  try {
    const scan = JSON.parse(row.result_json) as unknown
    return NextResponse.json({ scan })
  } catch {
    return NextResponse.json({ error: 'Invalid stored scan' }, { status: 500 })
  }
}
