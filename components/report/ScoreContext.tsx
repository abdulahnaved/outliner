'use client'

type Props = {
  currentScore: number
  distributionScores?: number[]
  datasetMedian?: number | null
  datasetAverage?: number | null
  percentile?: number | null
}

const AXIS_MAX = 110

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n))
}

/** Position 0–110 as percentage (0–100) for the axis. */
function axisPct(score: number) {
  return (clamp(score, 0, AXIS_MAX) / AXIS_MAX) * 100
}

function median(values: number[]) {
  if (values.length === 0) return null
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  if (sorted.length % 2 === 0) return (sorted[mid - 1] + sorted[mid]) / 2
  return sorted[mid]
}

function average(values: number[]) {
  if (values.length === 0) return null
  return values.reduce((a, b) => a + b, 0) / values.length
}

function percentile(values: number[], x: number) {
  if (values.length === 0) return null
  const belowOrEqual = values.filter((v) => v <= x).length
  return (belowOrEqual / values.length) * 100
}

export function ScoreContext({
  currentScore,
  distributionScores,
  datasetMedian,
  datasetAverage,
  percentile: percentileProp
}: Props) {
  const dist = (distributionScores && distributionScores.length > 0 ? distributionScores : []).map((s) =>
    clamp(Number(s), 0, AXIS_MAX)
  )

  const med = typeof datasetMedian === 'number' ? datasetMedian : median(dist)
  const avg = typeof datasetAverage === 'number' ? datasetAverage : average(dist)
  const pct = typeof percentileProp === 'number' ? percentileProp : percentile(dist, currentScore)

  return (
    <section className="space-y-4 rounded border border-white/15 bg-black/20 p-4">
      <header className="space-y-1">
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted">security score context</p>
        <p className="text-xs text-muted">
          Where this site sits among previously scanned sites (gray dots). Your site is the red dot.
        </p>
      </header>

      <div className="grid gap-3 text-xs text-muted sm:grid-cols-4">
        <div className="rounded border border-white/10 bg-black/15 p-3">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">current</p>
          <p className="mt-1 text-text tabular-nums">{Math.round(currentScore)}</p>
        </div>
        <div className="rounded border border-white/10 bg-black/15 p-3">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">percentile</p>
          <p className="mt-1 text-text tabular-nums">{pct == null ? '—' : `${pct.toFixed(0)}%`}</p>
        </div>
        <div className="rounded border border-white/10 bg-black/15 p-3">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">median</p>
          <p className="mt-1 text-text tabular-nums">{med == null ? '—' : med.toFixed(0)}</p>
        </div>
        <div className="rounded border border-white/10 bg-black/15 p-3">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">average</p>
          <p className="mt-1 text-text tabular-nums">{avg == null ? '—' : avg.toFixed(0)}</p>
        </div>
      </div>

      <div className="relative h-10 rounded border border-white/10 bg-black/15 px-3">
        {/* Axis track: 0–110 scale; right margin keeps the red dot inside when score is 110 */}
        <div className="absolute left-3 right-10 top-0 h-full">
          <div className="absolute inset-0 top-1/2 h-px -translate-y-1/2 bg-white/10" />
          {dist.map((s, idx) => (
            <span
              key={`${s}-${idx}`}
              className="absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/25"
              style={{ left: `${axisPct(s)}%` }}
              aria-hidden
            />
          ))}
          <span
            className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-red-600 shadow-glow"
            style={{ left: `${axisPct(currentScore)}%` }}
            aria-label="current site score"
          />
        </div>
        <div className="absolute -bottom-5 left-3 right-10 flex justify-between text-[10px] text-muted">
          <span>0</span>
          <span style={{ position: 'absolute', left: `${axisPct(100)}%`, transform: 'translateX(-50%)' }}>100</span>
          <span>110</span>
        </div>
      </div>
    </section>
  )
}

