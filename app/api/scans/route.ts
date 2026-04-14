import { NextResponse } from 'next/server'
import { getSessionUserId } from '@/lib/auth-server'
import { getDb } from '@/lib/db'

const MAX_LIST = 200

type Summary = {
  id: number
  input_target: string
  normalized_host: string
  scan_status: string
  created_at: string
  rule_score: number | null
  ml_score: number | null
}

function summarize(id: number, resultJson: string, createdAt: string): Summary {
  let input_target = ''
  let normalized_host = ''
  let scan_status = 'unknown'
  let rule_score: number | null = null
  let ml_score: number | null = null
  try {
    const j = JSON.parse(resultJson) as Record<string, unknown>
    input_target = typeof j.input_target === 'string' ? j.input_target : ''
    normalized_host = typeof j.normalized_host === 'string' ? j.normalized_host : ''
    scan_status = typeof j.scan_status === 'string' ? j.scan_status : 'unknown'
    const r = j.rule_score
    const r2 = j.rule_score_v2
    const r3 = j.rule_score_v3
    if (typeof r === 'number' && Number.isFinite(r)) rule_score = r
    else if (typeof r2 === 'number' && Number.isFinite(r2)) rule_score = r2
    else if (typeof r3 === 'number' && Number.isFinite(r3)) rule_score = r3
    const p = j.predicted_rule_score
    if (typeof p === 'number' && Number.isFinite(p)) ml_score = p
  } catch {
    // defaults
  }
  return {
    id,
    input_target,
    normalized_host,
    scan_status,
    created_at: createdAt,
    rule_score,
    ml_score
  }
}

export async function GET() {
  const userId = await getSessionUserId()
  if (userId === null) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
  const db = getDb()
  const rows = db
    .prepare(
      `SELECT id, result_json, created_at FROM saved_scans
       WHERE user_id = ? ORDER BY datetime(created_at) DESC LIMIT ?`
    )
    .all(userId, MAX_LIST) as { id: number; result_json: string; created_at: string }[]

  const scans = rows.map((r) => summarize(r.id, r.result_json, r.created_at))
  return NextResponse.json({ scans })
}

export async function POST(request: Request) {
  const userId = await getSessionUserId()
  if (userId === null) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  let body: unknown
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }
  const o = body as Record<string, unknown>
  const scan = o.scan
  if (scan === null || typeof scan !== 'object' || Array.isArray(scan)) {
    return NextResponse.json({ error: 'Field "scan" must be a JSON object' }, { status: 400 })
  }

  const s = scan as Record<string, unknown>
  if (typeof s.input_target !== 'string' || typeof s.scan_status !== 'string') {
    return NextResponse.json(
      { error: 'Scan must include input_target and scan_status' },
      { status: 400 }
    )
  }

  const json = JSON.stringify(scan)
  if (json.length > 12 * 1024 * 1024) {
    return NextResponse.json({ error: 'Scan payload too large' }, { status: 413 })
  }

  const db = getDb()
  const r = db
    .prepare('INSERT INTO saved_scans (user_id, result_json) VALUES (?, ?)')
    .run(userId, json)

  const id = Number(r.lastInsertRowid)
  return NextResponse.json({ id })
}
