'use client'

import { useState } from 'react'
import type { Issue, Severity, RuleCategory } from '../../lib/rules'
import type { ViewMode } from './ViewToggle'

type Props = {
  issues: Issue[]
  viewMode: ViewMode
  onIssueClick?: (issue: Issue) => void
  activeIssueId?: string | null
}

const severityStyles: Record<Severity, string> = {
  LOW: 'border-white/20 text-muted',
  MED: 'border-yellow-300/60 text-yellow-200',
  HIGH: 'border-red-400/70 text-red-300'
}

const SEVERITY_OPTS: { value: Severity | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All' },
  { value: 'HIGH', label: 'High' },
  { value: 'MED', label: 'Medium' },
  { value: 'LOW', label: 'Low' }
]

const CATEGORY_OPTS: { value: RuleCategory | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All' },
  { value: 'transport_security', label: 'Transport' },
  { value: 'content_security', label: 'Content' },
  { value: 'cookies', label: 'Cookies' },
  { value: 'policy_headers', label: 'Policy' },
  { value: 'cross_origin', label: 'Cross-Origin' }
]

export function IssueList({ issues, viewMode, onIssueClick, activeIssueId }: Props) {
  const [sevFilter, setSevFilter] = useState<Severity | 'ALL'>('ALL')
  const [catFilter, setCatFilter] = useState<RuleCategory | 'ALL'>('ALL')

  if (!issues || issues.length === 0) return null

  const filtered = issues.filter((i) => {
    if (sevFilter !== 'ALL' && i.severity !== sevFilter) return false
    if (catFilter !== 'ALL' && i.category !== catFilter) return false
    return true
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1">
          <span className="mr-1 text-[10px] uppercase tracking-[0.18em] text-muted">severity</span>
          {SEVERITY_OPTS.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => setSevFilter(o.value)}
              className={`rounded border px-2 py-0.5 text-[10px] font-medium transition-colors ${sevFilter === o.value ? 'border-white/30 bg-white/10 text-text' : 'border-white/10 text-muted hover:text-text/70'}`}
            >
              {o.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          <span className="mr-1 text-[10px] uppercase tracking-[0.18em] text-muted">category</span>
          {CATEGORY_OPTS.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => setCatFilter(o.value)}
              className={`rounded border px-2 py-0.5 text-[10px] font-medium transition-colors ${catFilter === o.value ? 'border-white/30 bg-white/10 text-text' : 'border-white/10 text-muted hover:text-text/70'}`}
            >
              {o.label}
            </button>
          ))}
        </div>
        <span className="ml-auto text-[10px] tabular-nums text-muted">
          {filtered.length}/{issues.length}
        </span>
      </div>

      {filtered.length === 0 ? (
        <p className="text-xs text-muted">No issues match the current filters.</p>
      ) : (
        <div className="space-y-3">
          {filtered.map((issue) => {
            const isActive = activeIssueId === issue.id
            return (
              <button
                key={issue.id}
                type="button"
                onClick={() => onIssueClick?.(issue)}
                className={`block w-full space-y-2 rounded border p-4 text-left transition-colors ${isActive ? 'border-teal-500/50 bg-teal-500/5' : 'border-white/15 bg-black/15 hover:border-white/25'}`}
              >
                <header className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.18em] text-muted">
                      {issue.category.replaceAll('_', ' ')}
                    </p>
                    <h3 className="mt-1 text-sm text-text">{issue.title}</h3>
                  </div>
                  <span
                    className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-wide ${severityStyles[issue.severity]}`}
                  >
                    {issue.severity}
                  </span>
                </header>
                <p className="text-xs text-muted">{issue.description}</p>
                <p className="text-xs text-text/90">
                  {viewMode === 'beginner' ? issue.recommendation : issue.recommendation}
                </p>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
