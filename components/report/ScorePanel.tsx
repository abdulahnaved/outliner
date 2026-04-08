'use client'

import type { ScoreMode } from './ScoreModeToggle'
import type { ViewMode } from './ViewToggle'

type Props = {
  ruleScore: number
  ruleGrade: string
  mlAvailable: boolean
  mlScore: number | null | undefined
  scoreMode: ScoreMode
  viewMode: ViewMode
}

function gradeColor(grade: string) {
  if (grade.startsWith('A')) return 'text-teal-300'
  if (grade.startsWith('B')) return 'text-green-300'
  if (grade.startsWith('C')) return 'text-yellow-200'
  if (grade.startsWith('D')) return 'text-orange-300'
  return 'text-red-400'
}

function agreementLabel(rule: number, ml: number | null | undefined): { text: string; color: string } {
  if (ml == null) return { text: 'ML unavailable', color: 'text-muted' }
  const diff = Math.abs(rule - ml)
  if (diff <= 5) return { text: 'Strong agreement', color: 'text-teal-300' }
  if (diff <= 15) return { text: 'Moderate agreement', color: 'text-yellow-200' }
  return { text: 'Notable divergence', color: 'text-orange-300' }
}

export function ScorePanel({ ruleScore, ruleGrade, mlAvailable, mlScore, scoreMode, viewMode }: Props) {
  const mlRound = typeof mlScore === 'number' ? Math.round(mlScore) : null
  const ruleRound = Math.round(ruleScore)
  const agreement = agreementLabel(ruleScore, mlScore)

  return (
    <section className="space-y-4 rounded border border-white/15 bg-black/20 p-4">
      {scoreMode === 'rule' && (
        <div className="space-y-3">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">rule-based score</p>
          <div className="flex items-baseline gap-3">
            <span className="text-5xl font-bold tabular-nums text-text">{ruleRound}</span>
            <span className={`text-2xl font-semibold ${gradeColor(ruleGrade)}`}>{ruleGrade}</span>
          </div>
          <p className="text-xs text-muted">
            {viewMode === 'beginner'
              ? 'A score based on publicly visible security signals like HTTPS, headers, cookies, and TLS. Higher is better (0\u2013110).'
              : 'Deterministic, category-capped assessment from passive header/TLS/cookie features. Range 0\u2013110.'}
          </p>
        </div>
      )}

      {scoreMode === 'ml' && (
        <div className="space-y-3">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">ml predicted score</p>
          {mlAvailable && mlRound != null ? (
            <div className="flex items-baseline gap-3">
              <span className="text-5xl font-bold tabular-nums text-red-300">{mlRound}</span>
              <span className="text-xs text-muted">predicted</span>
            </div>
          ) : (
            <p className="text-sm text-muted">ML prediction unavailable for this scan.</p>
          )}
          <p className="text-xs text-muted">
            {viewMode === 'beginner'
              ? 'A machine-learning model estimates the score based on patterns learned from hundreds of previously scanned sites.'
              : 'HistGradientBoosting regressor trained on passive scan features. Complements the rule engine.'}
          </p>
        </div>
      )}

      {scoreMode === 'compare' && (
        <div className="space-y-4">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">score comparison</p>
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded border border-white/10 bg-black/15 p-3 text-center">
              <p className="text-[10px] uppercase tracking-[0.18em] text-muted">Rule</p>
              <p className="mt-1 text-3xl font-bold tabular-nums text-text">{ruleRound}</p>
              <p className={`mt-0.5 text-sm font-semibold ${gradeColor(ruleGrade)}`}>{ruleGrade}</p>
            </div>
            <div className="rounded border border-white/10 bg-black/15 p-3 text-center">
              <p className="text-[10px] uppercase tracking-[0.18em] text-muted">ML</p>
              <p className="mt-1 text-3xl font-bold tabular-nums text-red-300">{mlRound ?? '\u2014'}</p>
              <p className="mt-0.5 text-sm text-muted">{mlAvailable ? 'predicted' : 'n/a'}</p>
            </div>
          </div>
          <div className="rounded border border-white/10 bg-black/15 px-3 py-2">
            <span className={`text-sm font-medium ${agreement.color}`}>{agreement.text}</span>
            {mlRound != null && (
              <span className="ml-2 text-xs text-muted">
                (\u0394 {Math.abs(ruleRound - mlRound)} pts)
              </span>
            )}
            <p className="mt-1 text-[11px] text-muted">
              {viewMode === 'beginner'
                ? 'When the rule score and ML estimate are close, both methods see a similar security posture. Large gaps may highlight unusual configurations.'
                : 'Agreement indicates the rule engine and the learned model converge on the same security signal. Divergence often traces to features the rule engine caps but the model weighs differently.'}
            </p>
          </div>
        </div>
      )}
    </section>
  )
}
