'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { ReportHeader } from '../../components/report/ReportHeader'
import { ScorePanel } from '../../components/report/ScorePanel'
import { ScoreContext } from '../../components/report/ScoreContext'
import { IssueList } from '../../components/report/IssueList'
import { EvidenceSnapshot } from '../../components/report/EvidenceSnapshot'
import { FailedScanNotice } from '../../components/report/FailedScanNotice'
import { buildCategorySummaries, evaluateRules } from '../../lib/rules'
import type { Issue, RuleCategory } from '../../lib/rules'
import { ModelInsight } from '../../components/report/ModelInsight'
import { SecurityProfile } from '../../components/report/SecurityProfile'
import { ViewToggle } from '../../components/report/ViewToggle'
import type { ViewMode } from '../../components/report/ViewToggle'
import { ScoreModeToggle } from '../../components/report/ScoreModeToggle'
import type { ScoreMode } from '../../components/report/ScoreModeToggle'
import { TopDrivers } from '../../components/report/TopDrivers'
import { Collapsible } from '../../components/report/Collapsible'
import { BeginnerSummary } from '../../components/report/BeginnerSummary'

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

const ISSUE_TO_EVIDENCE: Record<string, string> = {
  missing_https: 'tls',
  missing_hsts: 'headers',
  weak_tls: 'tls',
  cert_expired: 'tls',
  cert_expiring: 'tls',
  missing_csp: 'headers',
  csp_unsafe_inline: 'headers',
  csp_unsafe_eval: 'headers',
  csp_low_score: 'headers',
  cookie_no_secure: 'headers',
  cookie_no_httponly: 'headers',
  cookie_no_samesite: 'headers',
  referrer_policy_missing: 'headers',
  permissions_policy_missing: 'headers',
  x_frame_missing: 'headers',
  x_content_type_missing: 'headers',
  cors_wildcard_with_credentials: 'headers'
}

function formatTimestamp() {
  return new Date().toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit'
  })
}

export default function ReportPage({ searchParams }: { searchParams: { target?: string } }) {
  const target = searchParams.target || ''
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<ScanResult | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('beginner')
  const [scoreMode, setScoreMode] = useState<ScoreMode>('rule')
  const [activeIssueId, setActiveIssueId] = useState<string | null>(null)
  const [evidenceHighlight, setEvidenceHighlight] = useState<string | null>(null)

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
      } catch { return null }
    }
    const cached = typeof window !== 'undefined' ? fromCache() : null
    if (cached) { setData(cached); setLoading(false) } else { setLoading(true) }

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
        try { window.localStorage.setItem('outliner:lastScan', JSON.stringify(json)) } catch {}
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Could not reach scanner backend.'))
      .finally(() => setLoading(false))
  }, [target])

  const timestamp = useMemo(() => formatTimestamp(), [])
  const issues = useMemo(() => (data ? evaluateRules(data.features ?? {}) : []), [data])
  const categories = useMemo(() => {
    if (!data) return []
    return buildCategorySummaries(issues, data.features ?? {}).map((s) => ({
      title: s.title, strength: s.strength, category: s.category, triggered: s.triggered
    }))
  }, [data, issues])

  const handleIssueClick = useCallback((issue: Issue) => {
    const next = activeIssueId === issue.id ? null : issue.id
    setActiveIssueId(next)
    const evSection = next ? (ISSUE_TO_EVIDENCE[issue.id] ?? 'headers') : null
    setEvidenceHighlight(evSection)
    if (evSection) {
      setTimeout(() => {
        document.getElementById(`evidence-${evSection}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }, 100)
    }
  }, [activeIssueId])

  const handleCategoryJump = useCallback((_cat: RuleCategory) => {
    document.getElementById('section-security-profile')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  // --- Early returns for error/loading/missing ---

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
        <p className="text-xs text-muted">{loading ? 'Scanning\u2026' : 'Loading report\u2026'}</p>
      </div>
    )
  }

  if (data.scan_status === 'failed') {
    return (
      <div className="space-y-10">
        <ReportHeader target={data.input_target || target} normalizedHost={data.normalized_host} timestamp={timestamp} status="failed" />
        <FailedScanNotice scanErrorType={data.scan_error_type} scanErrorMessage={data.scan_error_message} />
        <section className="space-y-3 rounded border border-white/15 bg-black/20 p-4">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">available metadata</p>
          <div className="text-xs text-muted">
            <p className="break-words">requested url: {data.requested_url}</p>
            <p className="break-words">final url: {data.final_url ?? '\u2014'}</p>
            <p>status code: {data.final_status_code ?? '\u2014'}</p>
          </div>
        </section>
      </div>
    )
  }

  // --- SUCCESS ---

  const ruleScore = data.rule_score ?? 0
  const ruleGrade = data.rule_grade ?? '\u2014'

  return (
    <div className="space-y-8">
      {/* Header + view toggle (shared) */}
      <div className="space-y-4">
        <ReportHeader
          target={data.input_target || target}
          normalizedHost={data.normalized_host}
          timestamp={timestamp}
          status="success"
        />
        <ViewToggle mode={viewMode} onChange={setViewMode} />
      </div>

      {/* ====== BEGINNER VIEW ====== */}
      {viewMode === 'beginner' && (
        <BeginnerSummary
          ruleScore={ruleScore}
          ruleGrade={ruleGrade}
          mlAvailable={Boolean(data.prediction_available)}
          mlScore={data.predicted_rule_score}
          percentile={data.score_context?.percentile ?? null}
          categories={categories}
          issues={issues}
          features={data.features ?? {}}
        />
      )}

      {/* ====== TECHNICAL VIEW ====== */}
      {viewMode === 'technical' && (
        <div className="space-y-8">
          {/* Score mode toggle + score panel */}
          <div className="space-y-4">
            <ScoreModeToggle mode={scoreMode} onChange={setScoreMode} />
            <ScorePanel
              ruleScore={ruleScore}
              ruleGrade={ruleGrade}
              mlAvailable={Boolean(data.prediction_available)}
              mlScore={data.predicted_rule_score}
              scoreMode={scoreMode}
              viewMode={viewMode}
            />
          </div>

          {/* Score context */}
          <Collapsible title="score context" subtitle="Dataset distribution & percentile">
            <ScoreContext
              currentScore={ruleScore}
              distributionScores={data.score_context?.distribution_scores ?? []}
              datasetMedian={data.score_context?.dataset_median ?? null}
              datasetAverage={data.score_context?.dataset_average ?? null}
              percentile={data.score_context?.percentile ?? null}
            />
          </Collapsible>

          {/* Top drivers */}
          <TopDrivers
            features={data.features ?? {}}
            issues={issues}
            viewMode={viewMode}
            onCategoryClick={handleCategoryJump}
          />

          {/* Model insight */}
          <Collapsible title="model insight" subtitle="Feature importances & prediction confidence">
            <ModelInsight
              percentile={data.score_context?.percentile ?? null}
              predictionAvailable={Boolean(data.prediction_available)}
              features={data.features ?? undefined}
            />
          </Collapsible>

          {/* Security profile */}
          <Collapsible
            title="security profile"
            subtitle="Category-level strength assessment"
            id="section-security-profile"
          >
            <SecurityProfile
              categories={categories.map((c) => ({ title: c.title, strength: c.strength }))}
              issues={issues}
              viewMode={viewMode}
            />
          </Collapsible>

          {/* Recommendations (filterable, linked to evidence) */}
          <Collapsible
            title="recommendations"
            subtitle={`${issues.length} issue${issues.length === 1 ? '' : 's'} found`}
          >
            <IssueList
              issues={issues}
              viewMode={viewMode}
              onIssueClick={handleIssueClick}
              activeIssueId={activeIssueId}
            />
          </Collapsible>

          {/* Evidence snapshot */}
          <Collapsible title="evidence snapshot" subtitle="Response metadata & header evidence">
            <EvidenceSnapshot
              evidence={data.evidence}
              features={data.features}
              finalStatusCode={data.final_status_code}
              finalUrl={data.final_url}
              redirectCount={data.redirect_count ?? 0}
              responseTime={data.response_time ?? null}
              viewMode={viewMode}
              highlightSection={evidenceHighlight}
            />
          </Collapsible>
        </div>
      )}
    </div>
  )
}
