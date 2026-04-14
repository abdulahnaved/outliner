'use client'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useMemo, useState } from 'react'
import {
  buildCompareVerdict,
  digestScanPayload,
  extractMlScore,
  extractRuleScore
} from '@/lib/compareScans'
import type { CategorySummaryStrength } from '@/lib/rules'

type ScanPayload = Record<string, unknown>

function strengthTone(s: CategorySummaryStrength): string {
  if (s === 'Strong') return 'text-teal-300/90'
  if (s === 'Moderate') return 'text-yellow-200/90'
  if (s === 'Weak') return 'text-red-400/90'
  return 'text-muted'
}

function formatScore(n: number | null): string {
  if (n === null || Number.isNaN(n)) return '—'
  return String(Math.round(n * 10) / 10)
}

function CompareContent() {
  const searchParams = useSearchParams()
  const aRaw = searchParams.get('a') ?? ''
  const bRaw = searchParams.get('b') ?? ''

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [scanA, setScanA] = useState<ScanPayload | null>(null)
  const [scanB, setScanB] = useState<ScanPayload | null>(null)

  const idA = useMemo(() => parseInt(aRaw, 10), [aRaw])
  const idB = useMemo(() => parseInt(bRaw, 10), [bRaw])

  useEffect(() => {
    setError(null)
    setScanA(null)
    setScanB(null)

    if (!aRaw || !bRaw) {
      setLoading(false)
      setError('Choose two saved scans from the workspace or history to compare.')
      return
    }
    if (!Number.isFinite(idA) || !Number.isFinite(idB) || idA < 1 || idB < 1) {
      setLoading(false)
      setError('Invalid scan ids in the URL.')
      return
    }
    if (idA === idB) {
      setLoading(false)
      setError('Choose two different saved scans.')
      return
    }

    setLoading(true)
    const q = (id: number) => fetch(`/api/scans/${id}`, { credentials: 'include' })

    Promise.all([q(idA), q(idB)])
      .then(async ([ra, rb]) => {
        if (ra.status === 401 || rb.status === 401) {
          window.location.assign(
            '/login?next=' +
              encodeURIComponent(`/history/compare?a=${idA}&b=${idB}`)
          )
          return
        }
        const ja = (await ra.json().catch(() => null)) as { scan?: ScanPayload; error?: string }
        const jb = (await rb.json().catch(() => null)) as { scan?: ScanPayload; error?: string }
        if (!ra.ok) {
          throw new Error(typeof ja?.error === 'string' ? ja.error : 'Could not load first scan.')
        }
        if (!rb.ok) {
          throw new Error(typeof jb?.error === 'string' ? jb.error : 'Could not load second scan.')
        }
        if (!ja?.scan || !jb?.scan) {
          throw new Error('Invalid scan data.')
        }
        setScanA(ja.scan as ScanPayload)
        setScanB(jb.scan as ScanPayload)
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Could not load scans.')
      })
      .finally(() => setLoading(false))
  }, [aRaw, bRaw, idA, idB])

  const digest = useMemo(() => {
    if (!scanA || !scanB) return null
    const featA = (scanA.features ?? {}) as Record<string, unknown>
    const featB = (scanB.features ?? {}) as Record<string, unknown>
    const dA = digestScanPayload(featA)
    const dB = digestScanPayload(featB)
    const ruleA = extractRuleScore(scanA)
    const ruleB = extractRuleScore(scanB)
    const mlA = extractMlScore(scanA)
    const mlB = extractMlScore(scanB)
    const verdict = buildCompareVerdict(
      ruleA,
      ruleB,
      mlA,
      mlB,
      dA.issueCount,
      dB.issueCount,
      dA.categories,
      dB.categories
    )
    return {
      dA,
      dB,
      ruleA,
      ruleB,
      mlA,
      mlB,
      verdict,
      statusA: typeof scanA.scan_status === 'string' ? scanA.scan_status : 'unknown',
      statusB: typeof scanB.scan_status === 'string' ? scanB.scan_status : 'unknown',
      hostA: typeof scanA.input_target === 'string' ? scanA.input_target : '—',
      hostB: typeof scanB.input_target === 'string' ? scanB.input_target : '—'
    }
  }, [scanA, scanB])

  if (loading) {
    return (
      <div className="space-y-4 pt-2">
        <p className="text-sm text-muted">Loading comparison…</p>
      </div>
    )
  }

  if (error || !digest) {
    return (
      <div className="space-y-4 pt-2">
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted">compare</p>
        <p className="text-sm text-red-400">{error ?? 'Nothing to compare.'}</p>
        <div className="flex flex-wrap gap-4 text-xs font-semibold">
          <Link href="/dashboard" className="text-red-400/90 hover:text-red-300">
            ← Workspace
          </Link>
          <Link href="/history" className="text-red-400/90 hover:text-red-300">
            ← History
          </Link>
        </div>
      </div>
    )
  }

  const { dA, dB, ruleA, ruleB, mlA, mlB, verdict, statusA, statusB, hostA, hostB } = digest
  const short = (h: string) => (h.length > 36 ? `${h.slice(0, 33)}…` : h)

  const win = (side: 'a' | 'b' | 'tie', nameA: string, nameB: string) => {
    if (side === 'tie') return 'Tie'
    return side === 'a' ? short(nameA) : short(nameB)
  }

  const moreFindingsLabel =
    verdict.moreFindingsWorse === 'tie'
      ? 'Same number of findings'
      : verdict.moreFindingsWorse === 'a'
        ? `${short(hostA)} has more findings`
        : `${short(hostB)} has more findings`

  return (
    <div className="space-y-8 pt-2">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">compare</p>
          <h1 className="mt-2 text-xl font-semibold text-text">Saved scans</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Side-by-side view of two stored results. The scanner was not run again.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-4 text-[11px] font-mono">
          <Link href="/dashboard" className="text-muted hover:text-white">
            ← Workspace
          </Link>
          <Link href="/history" className="text-muted hover:text-white">
            ← History
          </Link>
        </div>
      </div>

      <section className="rounded border border-white/15 bg-black/25 p-4">
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted">summary</p>
        <ul className="mt-3 space-y-2 text-sm text-text">
          <li>
            <span className="text-muted">Higher rule score: </span>
            {win(verdict.ruleWinner, hostA, hostB)}
            {ruleA != null && ruleB != null ? ` (${formatScore(ruleA)} vs ${formatScore(ruleB)})` : null}
          </li>
          <li>
            <span className="text-muted">ML estimate: </span>
            {verdict.mlWinner === 'na'
              ? 'Not available for one or both'
              : `${win(verdict.mlWinner, hostA, hostB)}${mlA != null && mlB != null ? ` (${formatScore(mlA)} vs ${formatScore(mlB)})` : ''}`}
          </li>
          <li>
            <span className="text-muted">Findings count: </span>
            {moreFindingsLabel} ({dA.issueCount} vs {dB.issueCount})
          </li>
          <li>
            <span className="text-muted">Largest category gap: </span>
            {verdict.biggestCategoryGap > 0
              ? `${verdict.biggestCategoryTitle} (biggest strength mismatch between scans)`
              : 'No large category mismatch'}
          </li>
          <li>
            <span className="text-muted">Stronger overall (rule score, then fewer findings): </span>
            {win(verdict.strongerOverall, hostA, hostB)}
          </li>
        </ul>
      </section>

      <div className="grid grid-cols-2 items-start gap-4 max-sm:grid-cols-1">
        {[0, 1].map((col) => {
          const d = col === 0 ? dA : dB
          const rule = col === 0 ? ruleA : ruleB
          const ml = col === 0 ? mlA : mlB
          const status = col === 0 ? statusA : statusB
          const host = col === 0 ? hostA : hostB
          const id = col === 0 ? idA : idB
          const title = col === 0 ? 'First scan' : 'Second scan'
          return (
            <div
              key={id}
              className="flex min-w-0 flex-col rounded border border-white/10 bg-black/20 p-4"
            >
              <p className="text-[10px] uppercase tracking-[0.18em] text-muted">{title}</p>
              <p className="mt-2 truncate font-medium text-text" title={host}>
                {host}
              </p>
              <p className="text-[11px] text-muted">status: {status}</p>
              <div className="mt-4 grid grid-cols-2 gap-2 text-[11px] font-mono">
                <div className="rounded border border-white/10 bg-black/30 px-2 py-2">
                  <p className="text-muted">Rule score</p>
                  <p className="text-lg text-text">{formatScore(rule)}</p>
                </div>
                <div className="rounded border border-white/10 bg-black/30 px-2 py-2">
                  <p className="text-muted">ML score</p>
                  <p className="text-lg text-text">{formatScore(ml)}</p>
                </div>
              </div>
              <p className="mt-4 text-[10px] uppercase tracking-[0.14em] text-muted">Categories</p>
              <ul className="mt-2 space-y-1.5 text-xs">
                {d.categories.map((c) => (
                  <li key={c.category} className="flex justify-between gap-2">
                    <span className="text-muted">{c.title}</span>
                    <span className={strengthTone(c.strength)}>{c.strength}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-[10px] uppercase tracking-[0.14em] text-muted">
                Top findings ({d.issueCount})
              </p>
              <ul className="mt-2 list-inside list-disc space-y-1 text-[11px] text-muted">
                {d.issues.slice(0, 5).map((i) => (
                  <li key={i.id}>{i.title}</li>
                ))}
                {d.issues.length === 0 ? <li className="list-none">None flagged</li> : null}
              </ul>
              <Link
                href={`/report?scanId=${id}`}
                className="mt-4 inline-block text-[11px] font-semibold text-red-400/90 hover:text-red-300"
              >
                Open full report →
              </Link>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function ComparePage() {
  return (
    <Suspense
      fallback={<p className="pt-4 text-sm text-muted">Loading…</p>}
    >
      <CompareContent />
    </Suspense>
  )
}
