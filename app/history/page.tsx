'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
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

export default function HistoryPage() {
  const [scans, setScans] = useState<ScanRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    fetch('/api/scans', { credentials: 'include' })
      .then(async (res) => {
        if (res.status === 401) {
          window.location.assign('/login?next=/history')
          return
        }
        const j = (await res.json().catch(() => null)) as { error?: string; scans?: ScanRow[] }
        if (!res.ok) {
          throw new Error(typeof j?.error === 'string' ? j.error : 'Could not load history.')
        }
        setScans(j.scans ?? [])
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Could not load history.')
        setScans([])
      })
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="space-y-8 pt-2">
      <div>
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted">archive</p>
        <h1 className="mt-2 text-xl font-semibold text-text">All saved scans</h1>
        <p className="mt-2 max-w-xl text-sm text-muted">
          Full list of stored reports—open without re-running the scanner. New scans are saved from the{' '}
          <Link href="/dashboard" className="text-red-400/90 underline-offset-2 hover:underline">
            workspace
          </Link>
          .
        </p>
      </div>

      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      {scans !== null && scans.length >= 2 ? <CompareScanPicker scans={scans} /> : null}
      {scans !== null && scans.length === 1 ? (
        <p className="text-xs text-muted">
          Compare becomes available after you save at least two scans.
        </p>
      ) : null}

      {scans === null ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : scans.length === 0 ? (
        <div className="rounded border border-white/15 bg-black/20 p-6 text-sm text-muted">
          <p>No saved scans yet.</p>
          <Link
            href="/#scan"
            className="mt-3 inline-block text-xs font-semibold tracking-wide text-red-400 hover:text-red-300"
          >
            RUN A SCAN
          </Link>
        </div>
      ) : (
        <ul className="space-y-2">
          {scans.map((s) => (
            <li
              key={s.id}
              className="flex flex-col gap-3 rounded border border-white/10 bg-black/20 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-text">
                  {s.input_target || s.normalized_host || 'Scan'}
                </p>
                <p className="text-[11px] text-muted">{s.created_at}</p>
                <p className="mt-1 text-[11px] font-mono text-muted">
                  rule {formatScore(s.rule_score)}
                  {' · '}
                  ml {formatScore(s.ml_score)}
                </p>
              </div>
              <Link
                href={`/report?scanId=${s.id}`}
                className="shrink-0 rounded border border-white/20 px-3 py-1.5 text-center text-[11px] font-semibold tracking-wide text-text transition hover:border-red-500/50 hover:text-red-400"
              >
                OPEN REPORT
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
