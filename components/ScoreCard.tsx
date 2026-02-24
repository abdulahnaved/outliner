type ScoreCardProps = {
  score: number
  grade: string
}

export function ScoreCard({ score, grade }: ScoreCardProps) {
  const clamped = Math.max(0, Math.min(100, score))

  return (
    <section className="space-y-4 rounded border border-white/15 bg-black/20 p-4">
      <div className="flex items-baseline justify-between gap-4">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">overall score</p>
          <div className="mt-1 flex items-baseline gap-3">
            <span className="text-4xl font-semibold tabular-nums">{clamped}</span>
            <span className="rounded border border-white/15 px-2 py-0.5 text-xs text-muted">
              grade {grade}
            </span>
          </div>
        </div>
      </div>
      <div className="h-1.5 w-full rounded-full bg-white/5">
        <div
          className="h-full rounded-full bg-accent shadow-glow"
          style={{ width: `${clamped}%` }}
        />
      </div>
      <p className="text-[11px] text-muted">
        A simple synthetic score summarizing public signals. Use it as a waypoint, not a verdict.
      </p>
    </section>
  )
}

