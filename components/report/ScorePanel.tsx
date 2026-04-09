'use client'

import type { ScoreMode } from './ScoreModeToggle'
import type { ViewMode } from './ViewToggle'
import { compareDivergence, type MlReliability } from '../../lib/reportNarrative'
import { MlReliabilityPanel } from './MlReliabilityPanel'

type Props = {
  ruleScore: number
  ruleGrade: string
  mlAvailable: boolean
  mlScore: number | null | undefined
  scoreMode: ScoreMode
  viewMode: ViewMode
  mlReliability: MlReliability
  predictionError?: string | null
}

function gradeColor(grade: string) {
  if (grade.startsWith('A')) return 'text-teal-300'
  if (grade.startsWith('B')) return 'text-green-300'
  if (grade.startsWith('C')) return 'text-yellow-200'
  if (grade.startsWith('D')) return 'text-orange-300'
  return 'text-red-400'
}

export function ScorePanel({
  ruleScore,
  ruleGrade,
  mlAvailable,
  mlScore,
  scoreMode,
  viewMode,
  mlReliability,
  predictionError
}: Props) {
  const mlRound = typeof mlScore === 'number' ? Math.round(mlScore) : null
  const ruleRound = Math.round(ruleScore)
  const deltaMlMinusRule = mlRound != null ? mlRound - ruleRound : null
  const absDelta = deltaMlMinusRule != null ? Math.abs(deltaMlMinusRule) : null
  const div = absDelta != null ? compareDivergence(absDelta) : null

  const compareLabel =
    div === 'strong_agreement'
      ? 'Strong agreement'
      : div === 'moderate_divergence'
        ? 'Moderate divergence'
        : 'Large divergence'

  const compareColor =
    div === 'strong_agreement'
      ? 'text-teal-300'
      : div === 'moderate_divergence'
        ? 'text-yellow-200'
        : 'text-orange-300'

  const explainParagraphs = (() => {
    if (div == null || mlRound == null) return { a: '', b: '' }
    if (div === 'strong_agreement') {
      return {
        a: 'Both the learned model and the rule engine land on a similar posture from passive signals alone.',
        b: 'Use this as a stable read: neither lens is flagging a sharp mismatch.'
      }
    }
    if (div === 'moderate_divergence') {
      return {
        a: 'The gap is large enough to notice. The model is often more sensitive to how passive signals combine; the rule engine applies category caps and explicit heuristics.',
        b: 'Interpret disagreement as a tension between two estimators, not as one being “wrong.”'
      }
    }
    return {
      a: 'The gap is substantial. The rule engine may be hitting a ceiling or floor while the model weights feature interactions differently.',
      b: 'Large divergence usually means “worth inspecting the evidence blocks”—unusual headers, CSP shape, or cookie mix often explain the split.'
    }
  })()

  return (
    <section
      className={`space-y-4 rounded border p-4 transition-colors ${
        scoreMode === 'ml' && mlAvailable && mlRound != null
          ? 'border-red-500/25 bg-gradient-to-b from-red-950/20 to-black/20'
          : 'border-white/15 bg-black/20'
      }`}
    >
      {scoreMode === 'rule' && (
        <div className="space-y-3">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">Deterministic baseline</p>
          <h2 className="text-sm font-semibold tracking-tight text-text">Rule-based assessment</h2>
          <div className="flex items-baseline gap-3">
            <span className="text-5xl font-bold tabular-nums text-text">{ruleRound}</span>
            <span className={`text-2xl font-semibold ${gradeColor(ruleGrade)}`}>{ruleGrade}</span>
          </div>
          <p className="text-xs text-muted">
            {viewMode === 'beginner'
              ? 'A transparent, repeatable score from visible signals (HTTPS, headers, cookies, TLS). It is a baseline, not a full audit.'
              : 'Interpretable heuristic: fixed rules, category caps, and passive features only. Use it as a reference engine alongside the learned estimate.'}
          </p>
        </div>
      )}

      {scoreMode === 'ml' && (
        <div className="space-y-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">Primary assessment</p>
            <h2 className="mt-1 text-sm font-semibold tracking-tight text-text">Learned security assessment</h2>
          </div>

          {mlAvailable && mlRound != null ? (
            <>
              <div className="flex flex-wrap items-baseline gap-4">
                <span className="text-5xl font-bold tabular-nums text-red-300">{mlRound}</span>
                <div className="min-w-0">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-muted">ML estimate (0–110)</p>
                  <p className="mt-0.5 text-xs text-muted">
                    Regressor trained on passive scan features; predicts an expected rule-like score from the same signal family.
                  </p>
                </div>
              </div>

              <div className="rounded border border-white/10 bg-black/25 px-3 py-2.5 text-[11px] text-muted">
                <p className="text-[10px] uppercase tracking-[0.18em] text-muted">Reference baseline</p>
                <p className="mt-1 text-text/90">
                  Rule engine:{' '}
                  <span className="font-semibold tabular-nums text-text">{ruleRound}</span>
                  <span className={`ml-2 ${gradeColor(ruleGrade)}`}>({ruleGrade})</span>
                </p>
                <p className="mt-1 text-muted">{predictionError ? `Model note: ${predictionError}` : 'Shown for contrast with the deterministic heuristic.'}</p>
              </div>

              <MlReliabilityPanel reliability={mlReliability} />
            </>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-muted">No learned score is available for this scan.</p>
              <p className="text-xs text-muted">
                The model may be disabled, missing, or failed to produce a prediction. Use the rule baseline and evidence sections; switch to{' '}
                <span className="text-text/80">Rule</span> to focus on the deterministic score.
              </p>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2.5 text-[11px] text-muted">
                <p className="text-[10px] uppercase tracking-[0.18em] text-muted">Rule baseline (available)</p>
                <p className="mt-1 text-text/90">
                  <span className="font-semibold tabular-nums text-text">{ruleRound}</span>
                  <span className={`ml-2 ${gradeColor(ruleGrade)}`}>{ruleGrade}</span>
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {scoreMode === 'compare' && (
        <div className="space-y-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">Analytical compare</p>
            <h2 className="mt-1 text-sm font-semibold tracking-tight text-text">Rule engine vs. learned model</h2>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            <div className="rounded border border-white/10 bg-black/15 p-3 text-center">
              <p className="text-[10px] uppercase tracking-[0.18em] text-muted">Rule (baseline)</p>
              <p className="mt-1 text-3xl font-bold tabular-nums text-text">{ruleRound}</p>
              <p className={`mt-0.5 text-sm font-semibold ${gradeColor(ruleGrade)}`}>{ruleGrade}</p>
            </div>
            <div className="rounded border border-white/10 bg-black/15 p-3 text-center">
              <p className="text-[10px] uppercase tracking-[0.18em] text-muted">ML (learned)</p>
              <p className="mt-1 text-3xl font-bold tabular-nums text-red-300">{mlRound ?? '—'}</p>
              <p className="mt-0.5 text-sm text-muted">{mlAvailable ? 'estimate' : 'unavailable'}</p>
            </div>
          </div>

          {mlRound != null && absDelta != null && deltaMlMinusRule != null ? (
            <div className="space-y-2 rounded border border-white/10 bg-black/15 px-3 py-2.5">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span className={`text-sm font-medium ${compareColor}`}>{compareLabel}</span>
                <span className="font-mono text-xs text-muted tabular-nums">
                  Δ (ML − Rule) = {deltaMlMinusRule > 0 ? '+' : ''}
                  {deltaMlMinusRule} pts
                </span>
                <span className="text-xs text-muted">magnitude {absDelta} pts</span>
              </div>
              <p className="text-[11px] leading-relaxed text-muted">{explainParagraphs.a}</p>
              <p className="text-[11px] leading-relaxed text-muted">{explainParagraphs.b}</p>
            </div>
          ) : (
            <p className="text-xs text-muted">ML estimate missing—comparison needs both scores.</p>
          )}
        </div>
      )}
    </section>
  )
}
