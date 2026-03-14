'use client'

type Props = {
  predictionAvailable: boolean
  predictedRuleScore?: number | null
}

export function MLEstimate({ predictionAvailable, predictedRuleScore }: Props) {
  return (
    <section className="space-y-3 rounded border border-white/15 bg-black/20 p-4">
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
        <span className="text-text/90">ML score</span> is an estimate from learned patterns over
        prior scans. It complements the rule score.
      </p>
    </section>
  )
}
