'use client'

import type { ExecutiveSummary } from '../../lib/reportNarrative'

type Props = {
  summary: ExecutiveSummary
}

export function ExecutiveSummaryStrip({ summary }: Props) {
  return (
    <section
      className="rounded border border-white/10 bg-black/25 px-4 py-3 text-[11px] leading-relaxed text-muted sm:px-5"
      aria-label="Executive summary"
    >
      <p className="text-[10px] uppercase tracking-[0.22em] text-muted/90">Executive summary</p>
      <div className="mt-2 space-y-1.5 text-text/85">
        <p>
          <span className="text-muted">Main weakness:</span> {summary.mainWeakness}
        </p>
        <p>
          <span className="text-muted">Main strength:</span> {summary.mainStrength}
        </p>
        <p>
          <span className="text-muted">Priority action:</span> {summary.priorityAction}
        </p>
      </div>
    </section>
  )
}
