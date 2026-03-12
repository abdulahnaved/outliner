'use client'

import { ScoreCard } from '../ScoreCard'

type Props = {
  ruleScore: number
  ruleGrade: string
  predictionAvailable: boolean
  predictedRuleScore?: number | null
}

export function OverallScoreCard({
  ruleScore,
  ruleGrade,
  predictionAvailable,
  predictedRuleScore
}: Props) {
  return (
    <section className="space-y-4 rounded border border-white/15 bg-black/20 p-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-3">
          <ScoreCard score={ruleScore} grade={ruleGrade} />
          <p className="text-[11px] text-muted">
            <span className="text-text/90">Rule score</span> is a deterministic assessment from the
            observed headers/TLS/cookie signals.
          </p>
        </div>
        <div className="space-y-3 rounded border border-white/15 bg-black/15 p-4">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">ML estimate</p>
          {predictionAvailable && typeof predictedRuleScore === 'number' ? (
            <div className="flex items-baseline gap-3">
              <span className="text-4xl font-semibold tabular-nums text-red-300">
                {Math.round(predictedRuleScore)}
              </span>
              <span className="text-xs text-muted">predicted score</span>
            </div>
          ) : (
            <p className="text-xs text-muted">ML score unavailable for this scan.</p>
          )}
          <p className="text-[11px] text-muted">
            <span className="text-text/90">ML score</span> is an estimate from learned patterns
            over prior scans. It complements the rule score.
          </p>
        </div>
      </div>
    </section>
  )
}

