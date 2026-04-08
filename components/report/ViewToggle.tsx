'use client'

export type ViewMode = 'beginner' | 'technical'

type Props = {
  mode: ViewMode
  onChange: (mode: ViewMode) => void
}

export function ViewToggle({ mode, onChange }: Props) {
  return (
    <div className="inline-flex items-center gap-0.5 rounded-md border border-white/15 bg-black/30 p-0.5 text-[10px] font-semibold uppercase tracking-[0.2em]">
      <button
        type="button"
        onClick={() => onChange('beginner')}
        className={`rounded px-3 py-1.5 transition-colors ${mode === 'beginner' ? 'bg-white/10 text-text' : 'text-muted hover:text-text/70'}`}
      >
        Beginner
      </button>
      <button
        type="button"
        onClick={() => onChange('technical')}
        className={`rounded px-3 py-1.5 transition-colors ${mode === 'technical' ? 'bg-white/10 text-text' : 'text-muted hover:text-text/70'}`}
      >
        Technical
      </button>
    </div>
  )
}
