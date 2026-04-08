'use client'

import { useState } from 'react'
import type { Issue, RuleCategory } from '../../lib/rules'

type Strength = 'Strong' | 'Moderate' | 'Weak' | 'Neutral'
type CategoryInfo = { title: string; strength: Strength; category: RuleCategory; triggered: Issue[] }

type Props = {
  ruleScore: number
  ruleGrade: string
  mlAvailable: boolean
  mlScore: number | null | undefined
  percentile: number | null | undefined
  categories: CategoryInfo[]
  issues: Issue[]
  features: Record<string, unknown>
}

function gradeEmoji(grade: string) {
  if (grade.startsWith('A')) return '\u2705'
  if (grade.startsWith('B')) return '\u2705'
  if (grade.startsWith('C')) return '\u26A0\uFE0F'
  if (grade.startsWith('D')) return '\u26A0\uFE0F'
  return '\u274C'
}

function gradeColor(grade: string) {
  if (grade.startsWith('A')) return 'text-teal-300'
  if (grade.startsWith('B')) return 'text-green-300'
  if (grade.startsWith('C')) return 'text-yellow-200'
  if (grade.startsWith('D')) return 'text-orange-300'
  return 'text-red-400'
}

function strengthColor(s: Strength) {
  if (s === 'Strong') return 'border-teal-500/40 bg-teal-500/10 text-teal-300'
  if (s === 'Moderate') return 'border-yellow-500/40 bg-yellow-500/10 text-yellow-200'
  if (s === 'Weak') return 'border-red-500/40 bg-red-500/10 text-red-300'
  return 'border-blue-500/40 bg-blue-500/10 text-blue-300'
}

function strengthIcon(s: Strength) {
  if (s === 'Strong') return '\u2713'
  if (s === 'Weak') return '\u2717'
  if (s === 'Moderate') return '\u25CB'
  return '\u2014'
}

const CATEGORY_EXPLAIN: Record<string, string> = {
  'Transport Security': 'Is the connection between you and the site encrypted and secure?',
  'Content Security': 'Does the site restrict what scripts and content can run on the page?',
  'Cookies': 'Are login cookies protected from being stolen or misused?',
  'Browser / Policy Headers': 'Does the site use extra browser protections against common attacks?',
  'Cross-Origin Controls': 'Does the site prevent other websites from reading its data?'
}

export function BeginnerSummary({
  ruleScore,
  ruleGrade,
  mlAvailable,
  mlScore,
  percentile,
  categories,
  issues,
}: Props) {
  const [expandedCat, setExpandedCat] = useState<string | null>(null)
  const [showAllIssues, setShowAllIssues] = useState(false)
  const highIssues = issues.filter((i) => i.severity === 'HIGH')
  const medIssues = issues.filter((i) => i.severity === 'MED')
  const topIssues = showAllIssues ? issues : issues.slice(0, 4)

  const verdictText = ruleScore >= 85
    ? 'This site has strong security practices.'
    : ruleScore >= 60
      ? 'This site has decent security but some gaps need attention.'
      : ruleScore >= 40
        ? 'This site has notable security weaknesses that should be addressed.'
        : 'This site has serious security gaps. Significant improvements are needed.'

  return (
    <div className="space-y-8">
      {/* Big verdict card */}
      <section className="rounded-lg border border-white/15 bg-gradient-to-br from-black/40 via-black/20 to-black/40 p-6 text-center">
        <p className="text-[10px] uppercase tracking-[0.3em] text-muted">security assessment</p>
        <div className="mt-4 flex items-center justify-center gap-4">
          <span className="text-6xl font-bold tabular-nums text-text">{Math.round(ruleScore)}</span>
          <div className="text-left">
            <span className={`text-3xl font-bold ${gradeColor(ruleGrade)}`}>
              {gradeEmoji(ruleGrade)} {ruleGrade}
            </span>
            <p className="text-xs text-muted">out of 110</p>
          </div>
        </div>
        <p className="mx-auto mt-4 max-w-md text-sm text-text/80">{verdictText}</p>
        {percentile != null && (
          <p className="mt-2 text-xs text-muted">
            This site scores better than <span className="text-text">{Math.round(percentile)}%</span> of sites in our dataset.
          </p>
        )}
        {mlAvailable && typeof mlScore === 'number' && (
          <p className="mt-1 text-xs text-muted">
            Our AI model independently estimates a score of <span className="text-red-300 font-medium">{Math.round(mlScore)}</span>.
          </p>
        )}
      </section>

      {/* Quick status: high issues count */}
      {(highIssues.length > 0 || medIssues.length > 0) && (
        <section className="flex flex-wrap gap-3">
          {highIssues.length > 0 && (
            <div className="rounded border border-red-500/40 bg-red-500/10 px-4 py-2">
              <span className="text-2xl font-bold text-red-300">{highIssues.length}</span>
              <span className="ml-2 text-xs text-red-300/80">critical issue{highIssues.length > 1 ? 's' : ''}</span>
            </div>
          )}
          {medIssues.length > 0 && (
            <div className="rounded border border-yellow-500/40 bg-yellow-500/10 px-4 py-2">
              <span className="text-2xl font-bold text-yellow-200">{medIssues.length}</span>
              <span className="ml-2 text-xs text-yellow-200/80">warning{medIssues.length > 1 ? 's' : ''}</span>
            </div>
          )}
          {issues.length === 0 && (
            <div className="rounded border border-teal-500/40 bg-teal-500/10 px-4 py-2">
              <span className="text-sm font-medium text-teal-300">No issues detected</span>
            </div>
          )}
        </section>
      )}

      {/* Category cards — visual, clickable */}
      <section className="space-y-3">
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted">security areas</p>
        <p className="text-xs text-muted">Tap a category to see what was found.</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {categories.map((cat) => {
            const isOpen = expandedCat === cat.title
            return (
              <button
                key={cat.title}
                type="button"
                onClick={() => setExpandedCat(isOpen ? null : cat.title)}
                className={`rounded-lg border p-4 text-left transition-all ${isOpen ? 'border-teal-500/40 bg-teal-500/5' : 'border-white/15 bg-black/20 hover:border-white/25'}`}
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-text">{cat.title}</p>
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${strengthColor(cat.strength)}`}>
                    {strengthIcon(cat.strength)} {cat.strength}
                  </span>
                </div>
                <p className="mt-1.5 text-[11px] text-muted">{CATEGORY_EXPLAIN[cat.title] ?? ''}</p>
                {isOpen && (
                  <div className="mt-3 space-y-2 border-t border-white/10 pt-3">
                    {cat.triggered.length === 0 ? (
                      <p className="text-xs text-teal-300/80">
                        {cat.strength === 'Neutral' ? 'Not applicable for this site.' : 'No problems found here.'}
                      </p>
                    ) : (
                      cat.triggered.map((iss) => (
                        <div key={iss.id} className="text-xs">
                          <p className="font-medium text-text/90">{iss.title}</p>
                          <p className="mt-0.5 text-muted">{iss.recommendation}</p>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </button>
            )
          })}
        </div>
      </section>

      {/* What to fix — simplified issues */}
      {issues.length > 0 && (
        <section className="space-y-3">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">what to fix</p>
          <p className="text-xs text-muted">The most important improvements, in plain language.</p>
          <div className="space-y-2">
            {topIssues.map((iss) => (
              <div
                key={iss.id}
                className={`rounded border p-3 ${iss.severity === 'HIGH' ? 'border-red-500/30 bg-red-500/5' : iss.severity === 'MED' ? 'border-yellow-500/30 bg-yellow-500/5' : 'border-white/15 bg-black/15'}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm text-text/90">{iss.title}</p>
                  <span className={`shrink-0 rounded-full border px-1.5 py-0.5 text-[9px] font-semibold ${iss.severity === 'HIGH' ? 'border-red-400/60 text-red-300' : iss.severity === 'MED' ? 'border-yellow-300/50 text-yellow-200' : 'border-white/20 text-muted'}`}>
                    {iss.severity === 'HIGH' ? 'Critical' : iss.severity === 'MED' ? 'Warning' : 'Info'}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted">{iss.recommendation}</p>
              </div>
            ))}
          </div>
          {issues.length > 4 && !showAllIssues && (
            <button
              type="button"
              onClick={() => setShowAllIssues(true)}
              className="text-xs text-teal-400/80 hover:text-teal-300"
            >
              Show all {issues.length} issues \u2192
            </button>
          )}
        </section>
      )}
    </div>
  )
}
