'use client'

import type { MlReliability } from '../../lib/reportNarrative'

type Props = {
  reliability: MlReliability
}

const tierAccent: Record<MlReliability['tier'], string> = {
  higher: 'border-teal-500/35 bg-teal-500/5 text-teal-200/95',
  moderate: 'border-yellow-500/35 bg-yellow-500/5 text-yellow-100/90',
  lower: 'border-white/20 bg-black/20 text-muted'
}

export function MlReliabilityPanel({ reliability }: Props) {
  return (
    <div
      className={`rounded border px-3 py-2.5 text-[11px] leading-snug transition-colors ${tierAccent[reliability.tier]}`}
    >
      <p className="text-[10px] uppercase tracking-[0.2em] text-muted/90">Reliability</p>
      <p className="mt-1 font-medium text-text/95">{reliability.label}</p>
      <p className="mt-1 text-muted">{reliability.explanation}</p>
    </div>
  )
}
