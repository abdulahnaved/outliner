'use client'

type Strength = 'Strong' | 'Moderate' | 'Weak'

type Props = {
  categories: {
    title: string
    strength: Strength
    bullets: string[]
  }[]
}

function strengthBadge(strength: Strength) {
  if (strength === 'Strong') return 'border-teal-300/50 bg-teal-300/10 text-teal-200'
  if (strength === 'Moderate') return 'border-yellow-300/50 bg-yellow-300/10 text-yellow-200'
  return 'border-red-400/60 bg-red-500/10 text-red-300'
}

export function CategoryBreakdown({ categories }: Props) {
  return (
    <section className="space-y-4">
      <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
        security category breakdown
      </h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {categories.map((cat) => (
          <article key={cat.title} className="space-y-3 rounded border border-white/15 bg-black/20 p-4">
            <header className="flex items-center justify-between gap-3">
              <h3 className="text-sm text-text">{cat.title}</h3>
              <span
                className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-wide ${strengthBadge(cat.strength)}`}
              >
                {cat.strength}
              </span>
            </header>
            <ul className="space-y-1 text-xs text-muted">
              {cat.bullets.slice(0, 4).map((b, i) => (
                <li key={i} className="flex gap-2">
                  <span className="mt-[6px] h-1 w-1 rounded-full bg-white/20" aria-hidden />
                  <span>{b}</span>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </section>
  )
}

