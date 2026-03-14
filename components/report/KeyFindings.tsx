'use client'

type Props = {
  strengths: string[]
  weaknesses: string[]
}

export function KeyFindings({ strengths, weaknesses }: Props) {
  const strengthItems = strengths.length ? strengths : ['No strong signals detected yet.']
  const weaknessItems = weaknesses.length ? weaknesses : ['No critical weaknesses flagged.']

  return (
    <section className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-3 rounded border border-white/15 bg-black/20 p-4">
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted">strengths</p>
        <ul className="flex flex-wrap gap-2" role="list">
          {strengthItems.map((s, i) => (
            <li key={i}>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-teal-400/40 bg-teal-400/10 px-3 py-1.5 text-xs text-teal-200">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-teal-400/80" aria-hidden />
                {s}
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div className="space-y-3 rounded border border-white/15 bg-black/20 p-4">
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted">weaknesses</p>
        <ul className="flex flex-wrap gap-2" role="list">
          {weaknessItems.map((w, i) => (
            <li key={i}>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-red-400/40 bg-red-400/10 px-3 py-1.5 text-xs text-red-200">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-red-400/80" aria-hidden />
                {w}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
