'use client'

import { useEffect, useMemo, useState } from 'react'
import { ReportHeader } from '../../components/report/ReportHeader'
import { OverallScoreCard } from '../../components/report/OverallScoreCard'
import { ScoreContext } from '../../components/report/ScoreContext'
import { IssueList } from '../../components/report/IssueList'
import { EvidenceSnapshot } from '../../components/report/EvidenceSnapshot'
import { FailedScanNotice } from '../../components/report/FailedScanNotice'
import { buildCategorySummaries, evaluateRules } from '../../lib/rules'
import { ModelInsight } from '../../components/report/ModelInsight'
import { MLEstimate } from '../../components/report/MLEstimate'
import { SecurityProfile } from '../../components/report/SecurityProfile'

type ScanStatus = 'success' | 'failed'

type ScanResult = {
  input_target: string
  normalized_host: string
  requested_url: string
  final_url?: string | null
  final_status_code?: number | null
  timing_ms?: number | null
  redirect_count?: number
  response_time?: number
  features: Record<string, unknown>
  evidence?: Record<string, unknown> | null
  /** Primary display score (v2); backend sets rule_score = rule_score_v2 */
  rule_score?: number | null
  rule_grade?: string | null
  rule_label?: number | null
  rule_reasons?: string[]
  rule_score_v2?: number | null
  rule_grade_v2?: string | null
  rule_label_v2?: number | null
  rule_reasons_v2?: string[]
  rule_score_v3?: number | null
  rule_grade_v3?: string | null
  prediction_available?: boolean
  predicted_rule_score?: number | null
  ml_model_name?: string | null
  ml_model_variant?: string | null
  prediction_error?: string | null
  scan_status: ScanStatus
  scan_error_type?: string | null
  scan_error_message?: string | null
  score_context?: {
    distribution_scores: number[]
    dataset_median?: number | null
    dataset_average?: number | null
    percentile?: number | null
  } | null
}

function formatTimestamp() {
  return new Date().toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export default function ReportPage({ searchParams }: { searchParams: { target?: string } }) {
  const target = searchParams.target || ''
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<ScanResult | null>(null)

  useEffect(() => {
    if (!target) return

    setError(null)

    const fromCache = () => {
      try {
        const raw = window.localStorage.getItem('outliner:lastScan')
        if (!raw) return null
        const parsed = JSON.parse(raw) as ScanResult
        if (parsed && parsed.input_target === target) return parsed
        return null
      } catch {
        return null
      }
    }

    const cached = typeof window !== 'undefined' ? fromCache() : null
    if (cached) {
      setData(cached)
      setLoading(false)
    } else {
      setLoading(true)
    }

    fetch('http://localhost:8000/api/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target })
    })
      .then(async (res) => {
        const json = (await res.json().catch(() => null)) as ScanResult | null
        if (!res.ok) {
          const detail = (json as any)?.detail
          throw new Error(typeof detail === 'string' ? detail : 'Scan failed.')
        }
        if (!json) throw new Error('Empty scan response.')
        setData(json)
        try {
          window.localStorage.setItem('outliner:lastScan', JSON.stringify(json))
        } catch {
          // ignore
        }
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Could not reach scanner backend.')
      })
      .finally(() => setLoading(false))
  }, [target])

  const timestamp = useMemo(() => formatTimestamp(), [])

  const issues = useMemo(() => (data ? evaluateRules(data.features ?? {}) : []), [data])
  const categories = useMemo(() => {
    if (!data) return []
    const summaries = buildCategorySummaries(issues, data.features ?? {})
    return summaries.map((s) => ({
      title: s.title,
      strength: s.strength,
      bullets:
        s.category === 'cookies' && s.strength === 'Neutral'
          ? ['No cookies detected.']
          : s.triggered.length === 0
            ? ['No triggered issues in this category.']
            : s.triggered.slice(0, 4).map((i) => i.title)
    }))
  }, [data, issues])

  if (!target) {
    return (
      <div className="space-y-4">
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted">report</p>
        <p className="text-sm text-muted">No target provided. Go back and run a scan.</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <ReportHeader target={target} normalizedHost={null} timestamp={timestamp} status="failed" />
        <FailedScanNotice scanErrorType="unknown" scanErrorMessage={error} />
      </div>
    )
  }

  if (!data || loading) {
    return (
      <div className="space-y-4">
        <ReportHeader target={target} normalizedHost={null} timestamp={timestamp} status="loading" />
        <p className="text-xs text-muted">{loading ? 'Scanning…' : 'Loading report…'}</p>
      </div>
    )
  }

  const status = data.scan_status

  // FAILED state: minimal surface only
  if (status === 'failed') {
    return (
      <div className="space-y-10">
        <ReportHeader
          target={data.input_target || target}
          normalizedHost={data.normalized_host}
          timestamp={timestamp}
          status="failed"
        />
        <FailedScanNotice scanErrorType={data.scan_error_type} scanErrorMessage={data.scan_error_message} />
        <section className="space-y-3 rounded border border-white/15 bg-black/20 p-4">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">available metadata</p>
          <div className="text-xs text-muted">
            <p className="break-words">requested url: {data.requested_url}</p>
            <p className="break-words">final url: {data.final_url ?? '—'}</p>
            <p>status code: {data.final_status_code ?? '—'}</p>
          </div>
        </section>
      </div>
    )
  }

  // SUCCESS state: full structure
  const ruleScore = data.rule_score ?? 0
  const ruleGrade = data.rule_grade ?? '—'

  return (
    <div className="space-y-10">
      <ReportHeader
        target={data.input_target || target}
        normalizedHost={data.normalized_host}
        timestamp={timestamp}
        status="success"
      />

      <OverallScoreCard ruleScore={ruleScore} ruleGrade={ruleGrade} />

      <ScoreContext
        currentScore={ruleScore}
        distributionScores={data.score_context?.distribution_scores ?? []}
        datasetMedian={data.score_context?.dataset_median ?? null}
        datasetAverage={data.score_context?.dataset_average ?? null}
        percentile={data.score_context?.percentile ?? null}
      />

      <MLEstimate
        predictionAvailable={Boolean(data.prediction_available)}
        predictedRuleScore={data.predicted_rule_score}
      />

      <ModelInsight
        percentile={data.score_context?.percentile ?? null}
        predictionAvailable={Boolean(data.prediction_available)}
        features={data.features ?? undefined}
      />

      <SecurityProfile categories={categories.map((c) => ({ title: c.title, strength: c.strength }))} />

      <IssueList issues={issues} />

      <EvidenceSnapshot
        evidence={data.evidence}
        features={data.features}
        finalStatusCode={data.final_status_code}
        finalUrl={data.final_url}
        redirectCount={data.redirect_count ?? 0}
        responseTime={data.response_time ?? null}
      />
    </div>
  )
}

