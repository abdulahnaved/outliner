import Link from 'next/link'
import { DomainInput } from '../components/DomainInput'

export default function LandingPage() {
  return (
    <div className="space-y-32">
      <section
        id="scan"
        className="flex min-h-[70vh] flex-col items-center justify-center space-y-8"
      >
        <div className="max-w-xl space-y-6 text-center">
          <div className="space-y-3">
            <h1 className="text-3xl font-semibold sm:text-4xl">
              <span className="text-red-500">outliner</span>
            </h1>
            <h2 className="text-2xl text-muted sm:text-3xl">every surface tells a story</h2>
          </div>
          <p className="mt-1 text-sm text-muted">
            A calm, structured view of what your website exposes.
          </p>
        </div>
        <div className="w-full max-w-xl space-y-4 rounded border border-white/15 bg-black/25 p-4">
          <div className="space-y-2">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">run a scan</p>
            <p className="text-xs text-muted">
              Enter a domain to scan. You&apos;ll get a security report with scores and recommendations.
            </p>
          </div>
          <DomainInput />
        </div>
      </section>

      <section id="story" className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">story</h2>
        <div className="max-w-2xl space-y-3 text-sm text-muted">
          <p>
            Security posture is written in what your site already sends—headers, TLS, cookies, policy directives. Most tools either bury that in noise or assume you already know what to look for.
          </p>
          <p>
            Outliner reads those surfaces, scores them with a transparent rule set, and turns the result into one report: a single grade, a security profile across five categories, and concrete recommendations. No guessing, no crawling. Just what’s publicly visible, organized.
          </p>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">preview</h2>
        <p className="text-xs text-muted">
          After a scan you get: overall score and grade, score context (percentile vs other sites), ML estimate, security profile (five-category radar), and recommendations with evidence.
        </p>
        <div className="grid gap-4 rounded border border-white/15 bg-black/25 p-4 sm:grid-cols-2">
          <div className="space-y-2 rounded border border-white/10 bg-black/20 p-3">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">Overall score</p>
            <p className="text-sm text-text/90">Single rule-based score (0–110), grade (A+ to F), and optional ML predicted score.</p>
          </div>
          <div className="space-y-2 rounded border border-white/10 bg-black/20 p-3">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">Security profile</p>
            <p className="text-sm text-text/90">Pentagon radar: transport, content, cookies, policy headers, cross-origin. One-line interpretation.</p>
          </div>
          <div className="space-y-2 rounded border border-white/10 bg-black/20 p-3 sm:col-span-2">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">Recommendations</p>
            <p className="text-sm text-text/90">Issues with severity (LOW / MED / HIGH), description, and what to do. Evidence snapshot (headers, TLS) at the end.</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/#scan"
            className="inline-flex items-center rounded border border-red-500/60 bg-red-500/15 px-4 py-2 text-xs font-semibold tracking-wide text-red-500 shadow-glow transition hover:border-red-500 hover:bg-red-500/20"
          >
            Run scan
          </Link>
        </div>
      </section>

      <section id="method" className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">method</h2>
        <div className="space-y-4 text-sm text-muted">
          <p>We do a single request to your domain (following redirects), then inspect the response. No crawling, no content storage.</p>
          <ul className="list-inside list-disc space-y-1.5 text-muted">
            <li><span className="text-text/80">Transport:</span> HTTPS, HSTS, TLS version, certificate validity</li>
            <li><span className="text-text/80">Content:</span> Content-Security-Policy presence and strength</li>
            <li><span className="text-text/80">Cookies:</span> Secure, HttpOnly, SameSite on Set-Cookie</li>
            <li><span className="text-text/80">Policy headers:</span> Referrer-Policy, X-Frame-Options, X-Content-Type-Options, Permissions-Policy</li>
            <li><span className="text-text/80">Cross-origin:</span> CORS (e.g. wildcard with credentials)</li>
          </ul>
          <p>A rule-based score (0–110, category-capped) plus an optional ML estimate from patterns in prior scans. Report includes a security profile radar, recommendations, and raw evidence.</p>
          <p className="text-[11px] text-muted/80">
            Ethical use only: run it on domains you own or have permission to test.
          </p>
        </div>
        <div className="flex flex-wrap gap-4">
          <Link
            href="/method"
            className="inline-flex items-center text-xs text-red-500 underline-offset-4 hover:underline"
          >
            Full method →
          </Link>
          <Link
            href="/#scan"
            className="inline-flex items-center text-xs text-accent underline-offset-4 hover:underline"
          >
            Back to scan
          </Link>
        </div>
      </section>
    </div>
  )
}

