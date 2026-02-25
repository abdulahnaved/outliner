'use client'

import { useEffect, useState } from 'react'

type LastFetch = unknown

export function LastFetchDebug() {
  const [payload, setPayload] = useState<LastFetch | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      const raw = window.localStorage.getItem('outliner:lastFetch')
      if (!raw) return
      const parsed = JSON.parse(raw)
      setPayload(parsed)
    } catch {
      // ignore parse/storage errors
    }
  }, [])

  if (!payload) return null

  return (
    <section className="space-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
        raw fetch (phase 1)
      </h2>
      <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words rounded border border-white/15 bg-black/25 p-3 text-[11px] text-muted">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </section>
  )
}

