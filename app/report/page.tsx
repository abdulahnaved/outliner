'use client'

import { useEffect, useMemo, useState } from 'react'
import { ReportHeader } from '../../components/report/ReportHeader'
import { OverallScoreCard } from '../../components/report/OverallScoreCard'
import { ScoreContext } from '../../components/report/ScoreContext'
import { KeyFindings } from '../../components/report/KeyFindings'
import { CategoryBreakdown } from '../../components/report/CategoryBreakdown'
import { IssueList } from '../../components/report/IssueList'
import { EvidenceSnapshot } from '../../components/report/EvidenceSnapshot'
import { FailedScanNotice } from '../../components/report/FailedScanNotice'
import { buildCategorySummaries, evaluateRules } from '../../lib/rules'
import { ModelInsight } from '../../components/report/ModelInsight'

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
  rule_score?: number | null
  rule_grade?: string | null
  rule_label?: number | null
  rule_reasons?: string[]
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

function deriveFindings(features: Record<string, unknown>, issues: ReturnType<typeof evaluateRules>) {
  const strengths: string[] = []
  const weaknesses: string[] = []

  const hasHttps = Number(features.has_https ?? 0) === 1
  const hasHsts = Number(features.has_hsts ?? 0) === 1
  const weakTls = Number(features.weak_tls ?? 0) === 1
  const hasCsp = Number(features.has_csp ?? 0) === 1
  const redirectHttps = Number(features.redirect_http_to_https ?? 0) === 1
  const tlsVersion = Number(features.tls_version ?? 0)
  const totalCookies = Number(features.total_cookie_count ?? 0)
  const secureRatio = Number(features.secure_cookie_ratio ?? 0)
  const httpOnlyRatio = Number(features.httponly_cookie_ratio ?? 0)
  const sameSiteRatio = Number(features.samesite_cookie_ratio ?? 0)
  const corsWildcard = Number(features.cors_wildcard ?? 0) === 1
  const corsWildcardWithCreds = Number(features.cors_wildcard_with_credentials ?? 0) === 1

  if (hasHttps) strengths.push('HTTPS is available.')
  else weaknesses.push('No HTTPS detected.')
  if (hasHsts) strengths.push('HSTS is present.')
  else weaknesses.push('HSTS is missing.')
  if (weakTls) weaknesses.push('Weak TLS/cipher signal detected.')
  if (hasCsp) strengths.push('Content Security Policy is present.')
  else weaknesses.push('Content Security Policy is missing.')

  if (redirectHttps) strengths.push('HTTP redirects to HTTPS.')
  if (tlsVersion >= 1.2) strengths.push('Modern TLS version detected.')
  if (totalCookies > 0 && secureRatio === 1 && httpOnlyRatio === 1 && sameSiteRatio === 1) {
    strengths.push('Secure cookies configured (Secure, HttpOnly, SameSite).')
  }
  if (!corsWildcard && !corsWildcardWithCreds) {
    strengths.push('No wildcard CORS with credentials detected.')
  }

  for (const issue of issues.slice(0, 8)) {
    if (!weaknesses.includes(issue.title)) weaknesses.push(issue.title)
  }

  return { strengths, weaknesses }
}

export default function ReportPage({ searchParams }: { searchParams: { target?: string } }) {
  const target = searchParams.target || ''
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<ScanResult | null>(null)

  useEffect(() => {
    if (!target) return

    setLoading(true)
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
    if (cached) setData(cached)

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

  const { strengths, weaknesses } = useMemo(() => {
    if (!data) return { strengths: [], weaknesses: [] }
    return deriveFindings(data.features ?? {}, issues)
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
        <ReportHeader target={target} normalizedHost={null} timestamp={timestamp} status="failed" />
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

      <OverallScoreCard
        ruleScore={ruleScore}
        ruleGrade={ruleGrade}
        predictionAvailable={Boolean(data.prediction_available)}
        predictedRuleScore={data.predicted_rule_score}
      />

      <ScoreContext
        currentScore={ruleScore}
        distributionScores={data.score_context?.distribution_scores ?? []}
        datasetMedian={data.score_context?.dataset_median ?? null}
        datasetAverage={data.score_context?.dataset_average ?? null}
        percentile={data.score_context?.percentile ?? null}
      />

      <ModelInsight
        hasCookies={Number(data.features?.total_cookie_count ?? 0) > 0}
        hasHsts={Number(data.features?.has_hsts ?? 0) === 1}
        hasCsp={Number(data.features?.has_csp ?? 0) === 1}
        hasRedirectHttps={Number(data.features?.redirect_http_to_https ?? 0) === 1}
      />

      <KeyFindings strengths={strengths} weaknesses={weaknesses} />

      <CategoryBreakdown categories={categories} />

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

