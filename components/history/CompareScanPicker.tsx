'use client'

import { useRouter } from 'next/navigation'
import { useMemo, useState } from 'react'

export type ScanOption = {
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

function optionLabel(s: ScanOption): string {
  const host = s.input_target || s.normalized_host || 'scan'
  return `${host} · ${s.created_at} · rule ${formatScore(s.rule_score)}`
}

type Props = {
  scans: ScanOption[]
}

export function CompareScanPicker({ scans }: Props) {
  const router = useRouter()
  const [a, setA] = useState(String(scans[0]?.id ?? ''))
  const [b, setB] = useState(String(scans[1]?.id ?? ''))

  const canCompare = useMemo(() => {
    if (!a || !b || a === b) return false
    return true
  }, [a, b])

  const compare = () => {
    if (!canCompare) return
    router.push(`/history/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`)
  }

  return (
    <section className="rounded border border-white/15 bg-black/25 p-4">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted">compare</p>
      <p className="mt-1 text-sm text-text">
        Pick two saved scans to open a side-by-side comparison (no new scan).
      </p>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
        <label className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="text-[10px] uppercase tracking-[0.14em] text-muted">First scan</span>
          <select
            value={a}
            onChange={(e) => setA(e.target.value)}
            className="w-full rounded border border-white/15 bg-black/30 px-2 py-2 text-xs text-text focus:border-red-500/50 focus:outline-none"
          >
            {scans.map((s) => (
              <option key={s.id} value={String(s.id)}>
                {optionLabel(s)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="text-[10px] uppercase tracking-[0.14em] text-muted">Second scan</span>
          <select
            value={b}
            onChange={(e) => setB(e.target.value)}
            className="w-full rounded border border-white/15 bg-black/30 px-2 py-2 text-xs text-text focus:border-red-500/50 focus:outline-none"
          >
            {scans.map((s) => (
              <option key={`b-${s.id}`} value={String(s.id)}>
                {optionLabel(s)}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          disabled={!canCompare}
          onClick={() => compare()}
          className="h-10 shrink-0 rounded border border-red-500/70 bg-red-500/15 px-4 text-[11px] font-semibold tracking-wide text-red-500 transition hover:border-red-500 hover:bg-red-500/25 disabled:cursor-not-allowed disabled:opacity-40"
        >
          COMPARE SCANS
        </button>
      </div>
    </section>
  )
}
