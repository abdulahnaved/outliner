'use client'

export type ScoreMode = 'rule' | 'ml' | 'compare'

type Props = {
  mode: ScoreMode
  onChange: (mode: ScoreMode) => void
}

const OPTS: { value: ScoreMode; label: string }[] = [
  { value: 'rule', label: 'Rule' },
  { value: 'ml', label: 'ML' },
  { value: 'compare', label: 'Compare' }
]

export function ScoreModeToggle({ mode, onChange }: Props) {
  return (
    <div className="inline-flex items-center gap-0.5 rounded-md border border-white/15 bg-black/30 p-0.5 text-[10px] font-semibold uppercase tracking-[0.2em]">
      {OPTS.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={`rounded px-3 py-1.5 transition-colors ${mode === o.value ? 'bg-white/10 text-text' : 'text-muted hover:text-text/70'}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
