'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { DomainInput } from '@/components/DomainInput'
import { CompareScanPicker } from '@/components/history/CompareScanPicker'

type ScanRow = {
  id: number
  input_target: string
  normalized_host: string
  scan_status: string
  created_at: string
  rule_score: number | null
  ml_score: number | null
}

function formatScore(n: number | null): string {
  if (n === null || Number.isNaN(n)) return '—'
  return String(Math.round(n * 10) / 10)
}

export default function DashboardPage() {
  const [scans, setScans] = useState<ScanRow[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  const load = useCallback(() => {
    fetch('/api/scans', { credentials: 'include' })
      .then(async (res) => {
        if (res.status === 401) {
          window.location.assign('/login?next=/dashboard')
          return
        }
        const j = (await res.json().catch(() => null)) as { error?: string; scans?: ScanRow[] }
        if (!res.ok) {
          throw new Error(typeof j?.error === 'string' ? j.error : 'Could not load scans.')
        }
        setScans(j.scans ?? [])
      })
      .catch((e: unknown) => {
        setLoadError(e instanceof Error ? e.message : 'Could not load scans.')
        setScans([])
      })
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const recent = scans ? scans.slice(0, 5) : []

  return (
    <div className="space-y-10 pt-2">
      <header className="border-b border-white/10 pb-6">
        <h1 className="text-xl font-semibold text-text">Scan Workspace</h1>
      </header>

      {loadError ? <p className="text-sm text-red-400">{loadError}</p> : null}

      <section id="scan" className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">New scan</h2>
        <div className="rounded border border-white/15 bg-black/25 p-4">
          <DomainInput />
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">
            Recent saved scans
          </h2>
          {scans && scans.length > 0 ? (
            <Link
              href="/history"
              className="text-[11px] font-mono text-red-400/90 hover:text-red-300"
            >
              Full history →
            </Link>
          ) : null}
        </div>

        {scans === null ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : scans.length === 0 ? (
          <p className="rounded border border-white/10 bg-black/20 px-4 py-3 text-sm text-muted">
            No saved scans yet. Run one above—reports appear here after each successful scan.
          </p>
        ) : (
          <ul className="space-y-2">
            {recent.map((s) => (
              <li
                key={s.id}
                className="flex flex-col gap-2 rounded border border-white/10 bg-black/20 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-text">
                    {s.input_target || s.normalized_host || 'Scan'}
                  </p>
                  <p className="text-[11px] text-muted">{s.created_at}</p>
                  <p className="mt-0.5 text-[11px] font-mono text-muted">
                    rule {formatScore(s.rule_score)} · ml {formatScore(s.ml_score)}
                  </p>
                </div>
                <Link
                  href={`/report?scanId=${s.id}`}
                  className="shrink-0 rounded border border-white/20 px-3 py-1.5 text-center text-[11px] font-semibold text-text hover:border-red-500/50 hover:text-red-400"
                >
                  Open report
                </Link>
              </li>
            ))}
          </ul>
        )}

        {scans && scans.length >= 2 ? (
          <div className="pt-2">
            <CompareScanPicker scans={scans} />
          </div>
        ) : null}
      </section>
    </div>
  )
}
