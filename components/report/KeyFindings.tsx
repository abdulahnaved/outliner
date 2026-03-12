'use client'

type Props = {
  strengths: string[]
  weaknesses: string[]
}

export function KeyFindings({ strengths, weaknesses }: Props) {
  return (
    <section className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-3 rounded border border-white/15 bg-black/20 p-4">
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted">strengths</p>
        <ul className="space-y-1 text-xs text-muted">
          {(strengths.length ? strengths : ['No strong signals detected yet.']).map((s, i) => (
            <li key={i} className="flex gap-2">
              <span className="mt-[6px] h-1 w-1 rounded-full bg-teal-300/40" aria-hidden />
              <span>{s}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="space-y-3 rounded border border-white/15 bg-black/20 p-4">
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted">weaknesses</p>
        <ul className="space-y-1 text-xs text-muted">
          {(weaknesses.length ? weaknesses : ['No critical weaknesses flagged.']).map((w, i) => (
            <li key={i} className="flex gap-2">
              <span className="mt-[6px] h-1 w-1 rounded-full bg-red-400/40" aria-hidden />
              <span>{w}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

