'use client'

type Strength = 'Strong' | 'Moderate' | 'Weak' | 'Neutral'

const STRENGTH_TO_SCORE: Record<Strength, number> = {
  Strong: 90,
  Moderate: 60,
  Weak: 30,
  Neutral: 50
}

const CATEGORY_ORDER = [
  'Transport Security',
  'Content Security',
  'Cookies',
  'Browser / Policy Headers',
  'Cross-Origin Controls'
] as const

type Props = {
  categories: { title: string; strength: Strength }[]
}

function getScore(strength: Strength): number {
  return STRENGTH_TO_SCORE[strength] ?? 50
}

/** One-sentence interpretation from the lowest category/categories. */
function getInterpretation(categories: { title: string; strength: Strength; score: number }[]): string {
  const sorted = [...categories].sort((a, b) => a.score - b.score)
  const lowest = sorted[0]
  if (!lowest) return 'Security posture across categories.'
  const lowestScore = lowest.score
  const weak = sorted.filter((c) => c.score === lowestScore)
  const names = weak.map((c) => c.title.toLowerCase())
  if (weak.length === 0) return 'Strong overall posture.'
  if (weak.length === 1) {
    if (lowestScore >= 80) return 'Strong overall posture with minor variation across categories.'
    if (lowestScore >= 50) return `Overall posture is mixed; the main gap is in ${names[0]}.`
    return `Security posture is uneven, with the main weakness in ${names[0]}.`
  }
  if (weak.length === 2) {
    if (lowestScore >= 50) return `Overall posture is mixed, with gaps in ${names[0]} and ${names[1]}.`
    return `Security posture is uneven, with weaknesses in ${names[0]} and ${names[1]}.`
  }
  return `Security posture is uneven, with weaknesses concentrated in several areas.`
}

export function SecurityProfile({ categories }: Props) {
  const byTitle = new Map(categories.map((c) => [c.title, c]))
  const ordered = CATEGORY_ORDER.map((title) => {
    const cat = byTitle.get(title)
    const strength = cat?.strength ?? 'Neutral'
    return { title, strength, score: getScore(strength) }
  })

  const interpretation = getInterpretation(ordered)

  const size = 440
  const cx = size / 2
  const cy = size / 2
  const radius = 115
  const labelR = radius + 38
  const n = 5
  const angles = Array.from({ length: n }, (_, i) => (90 - i * 72) * (Math.PI / 180))

  const axisLabels = ['Transport', 'Content', 'Cookies', 'Policy', 'Cross-Origin']

  const axisEndPoints = angles.map((a) => ({
    x: cx + radius * Math.cos(a),
    y: cy - radius * Math.sin(a)
  }))

  const dataPoints = ordered.map((d, i) => {
    const r = radius * (d.score / 100)
    const a = angles[i]
    return { x: cx + r * Math.cos(a), y: cy - r * Math.sin(a) }
  })

  const polygonPoints = dataPoints.map((p) => `${p.x},${p.y}`).join(' ')
  const axisLines = axisEndPoints.map((p, i) => (
    <line
      key={i}
      x1={cx}
      y1={cy}
      x2={p.x}
      y2={p.y}
      stroke="rgba(255,255,255,0.15)"
      strokeWidth="1"
    />
  ))

  const gridCircles = [25, 50, 75].map((pct) => {
    const r = radius * (pct / 100)
    const pts = angles.map((a) => `${cx + r * Math.cos(a)},${cy - r * Math.sin(a)}`).join(' ')
    return <polygon key={pct} points={pts} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
  })

  return (
    <section className="space-y-4 rounded border border-white/15 bg-black/20 p-4">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted">security profile</p>
      <p className="text-[11px] text-muted">
        Each axis is 0–100. Scores are derived from the category strength: Strong = 90, Moderate =
        60, Weak = 30, Neutral = 50 (e.g. no cookies).
      </p>

      <div className="flex flex-col items-center">
        <svg
          viewBox={`0 0 ${size} ${size}`}
          className="h-[min(90vw,400px)] w-[min(90vw,400px)] max-w-full text-muted"
          aria-hidden
        >
            {gridCircles}
            {axisLines}
            <polygon
              points={polygonPoints}
              fill="rgba(45, 212, 191, 0.15)"
              stroke="rgba(45, 212, 191, 0.5)"
              strokeWidth="1.5"
            />
            {ordered.map((d, i) => {
              const a = angles[i]
              const lx = cx + labelR * Math.cos(a)
              const ly = cy - labelR * Math.sin(a)
              return (
                <text
                  key={d.title}
                  x={lx}
                  y={ly}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  style={{ fill: 'rgba(255,255,255,0.7)', fontSize: 11 }}
                >
                  {axisLabels[i]}
                </text>
              )
            })}
        </svg>
        <p className="mt-4 max-w-2xl text-center text-sm text-text/90">{interpretation}</p>
      </div>
    </section>
  )
}
