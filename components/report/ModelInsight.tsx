'use client'

type Props = {
  hasCookies: boolean
  hasHsts: boolean
  hasCsp: boolean
  hasRedirectHttps: boolean
}

export function ModelInsight({ hasCookies, hasHsts, hasCsp, hasRedirectHttps }: Props) {
  const bullets: string[] = []

  bullets.push('cookie configuration (presence, flags, and counts)')
  bullets.push('HSTS policy strength and max-age')
  bullets.push(hasCsp ? 'how strictly Content Security Policy is configured' : 'whether Content Security Policy is present')
  bullets.push(hasRedirectHttps ? 'how consistently HTTP redirects to HTTPS' : 'whether HTTP is redirected to HTTPS')

  return (
    <section className="space-y-3 rounded border border-white/15 bg-black/20 p-4">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted">model insight</p>
      <p className="text-xs text-muted">
        The ML estimate is generally influenced by patterns in a few key areas:
      </p>
      <ul className="space-y-1 text-xs text-muted">
        {bullets.map((b, i) => (
          <li key={i} className="flex gap-2">
            <span className="mt-[6px] h-1 w-1 rounded-full bg-white/30" aria-hidden />
            <span>{b}</span>
          </li>
        ))}
      </ul>
      <p className="text-[11px] text-muted/80">
        Across the scanned dataset, cookie-related features and policy headers were among the strongest predictors of
        overall security posture.
      </p>
    </section>
  )
}

