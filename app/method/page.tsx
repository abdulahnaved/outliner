import Link from 'next/link'

export const metadata = {
  title: 'Method — outliner',
  description: 'How Outliner scans and scores your website: passive inspection, categories, and scoring.'
}

export default function MethodPage() {
  return (
    <div className="space-y-16">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold sm:text-4xl">method</h1>
        <p className="max-w-xl text-sm text-muted">
          How we scan, what we look at, and how the score is produced.
        </p>
      </div>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">overview</h2>
        <p className="max-w-2xl text-sm text-muted">
          Outliner performs a passive scan: one HTTP request to your domain (following redirects to the final URL), then inspection of the response. We do not crawl pages, execute JavaScript, or store page content. Only headers, TLS metadata, and cookie attributes are used to build the report.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">what we scan</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2 rounded border border-white/15 bg-black/20 p-4">
            <p className="text-xs font-medium text-text/90">Transport security</p>
            <p className="text-xs text-muted">HTTPS availability, redirect to HTTPS, HSTS (max-age, includeSubDomains, preload), TLS version and cipher, certificate validity and expiry.</p>
          </div>
          <div className="space-y-2 rounded border border-white/15 bg-black/20 p-4">
            <p className="text-xs font-medium text-text/90">Content security</p>
            <p className="text-xs text-muted">Content-Security-Policy presence, quality (default-src, object-src, unsafe-inline/unsafe-eval), and a derived CSP strength score.</p>
          </div>
          <div className="space-y-2 rounded border border-white/15 bg-black/20 p-4">
            <p className="text-xs font-medium text-text/90">Cookies</p>
            <p className="text-xs text-muted">Set-Cookie attributes: Secure, HttpOnly, SameSite. We report ratios and flag missing flags; no cookies is treated as neutral.</p>
          </div>
          <div className="space-y-2 rounded border border-white/15 bg-black/20 p-4">
            <p className="text-xs font-medium text-text/90">Policy headers</p>
            <p className="text-xs text-muted">Referrer-Policy (strict vs weak), X-Frame-Options, X-Content-Type-Options: nosniff, Permissions-Policy.</p>
          </div>
          <div className="space-y-2 rounded border border-white/15 bg-black/20 p-4 sm:col-span-2">
            <p className="text-xs font-medium text-text/90">Cross-origin</p>
            <p className="text-xs text-muted">CORS headers (Access-Control-Allow-Origin, credentials). We flag wildcard origin with credentials as high risk.</p>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">how we score</h2>
        <div className="max-w-2xl space-y-3 text-sm text-muted">
          <p>
            <span className="text-text/90">Rule score (0–110):</span> A deterministic score from the observed signals. Each category (transport, content, cookies, policy headers, cross-origin) has a cap so one weak area cannot dominate. Bonuses (e.g. HSTS preload) apply only when the penalty score is already high. Grade (A+ to F) is mapped from the final score.
          </p>
          <p>
            <span className="text-text/90">Learned estimate:</span> A model trained on prior scans predicts the rule-style score from the same passive feature set. The report provides Rule, ML, and Compare modes so the deterministic baseline and learned perspective can be read side by side.
          </p>
          <p>
            The report also shows where your score sits in the distribution of previously scanned sites (percentile) and a security profile radar (five categories, 0–100 per axis derived from Strong/Moderate/Weak/Neutral).
          </p>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">what we don’t do</h2>
        <ul className="max-w-2xl list-inside list-disc space-y-1 text-sm text-muted">
          <li>We do not crawl or follow links.</li>
          <li>We do not execute JavaScript or render the page.</li>
          <li>We do not store or log page content.</li>
          <li>We do not perform active vulnerability checks or exploitation.</li>
        </ul>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">ethical use</h2>
        <p className="max-w-2xl text-sm text-muted">
          Run Outliner only on domains you own or have explicit permission to test. The tool is intended for security awareness and improvement, not for probing systems without authorization.
        </p>
      </section>

      <div className="pt-4">
        <Link
          href="/#scan"
          className="inline-flex items-center rounded border border-red-500/60 bg-red-500/15 px-4 py-2 text-xs font-semibold tracking-wide text-red-500 transition hover:border-red-500 hover:bg-red-500/20"
        >
          Run scan
        </Link>
      </div>
    </div>
  )
}
