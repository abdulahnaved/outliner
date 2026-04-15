import { NextResponse } from 'next/server'

const DEFAULT_SCANNER_URL = 'http://localhost:8000'

export async function POST(request: Request) {
  let body: unknown
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const o = body as Record<string, unknown>
  const target = typeof o.target === 'string' ? o.target.trim() : ''
  if (!target) {
    return NextResponse.json({ error: 'Field "target" is required' }, { status: 400 })
  }

  const base = (process.env.OUTLINER_SCANNER_URL || DEFAULT_SCANNER_URL).replace(/\/+$/, '')
  const url = `${base}/api/scan`

  // Proxy to the Python backend so the browser never hardcodes localhost
  // and we avoid CORS issues during demos.
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target })
  })

  const text = await res.text()
  return new NextResponse(text, {
    status: res.status,
    headers: { 'Content-Type': res.headers.get('content-type') || 'application/json' }
  })
}

