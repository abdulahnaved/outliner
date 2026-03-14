'use client'

import { ScoreCard } from '../ScoreCard'

type Props = {
  ruleScore: number
  ruleGrade: string
}

export function OverallScoreCard({ ruleScore, ruleGrade }: Props) {
  return (
    <section className="space-y-4 rounded border border-white/15 bg-black/20 p-4">
      <div className="space-y-3">
        <ScoreCard score={ruleScore} grade={ruleGrade} />
        <p className="text-[11px] text-muted">
          <span className="text-text/90">Rule score</span> is a deterministic assessment from the
          observed headers/TLS/cookie signals.
        </p>
      </div>
    </section>
  )
}

