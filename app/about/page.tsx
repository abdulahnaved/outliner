import Link from 'next/link'

export default function AboutPage() {
  return (
    <div className="space-y-24">
      <section className="space-y-6">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold sm:text-4xl">what it is</h1>
          <p className="max-w-xl text-sm text-muted">
            Outliner is a security report tool. It reads what your website already exposes—headers, TLS, cookies, policy directives—and turns it into one score, a category breakdown, and concrete recommendations.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-2 rounded border border-white/15 bg-black/25 p-3">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">reads</p>
            <p className="text-sm text-text/90">
              Headers, TLS, cookies, and policy signals from a single request (no crawling).
            </p>
          </div>
          <div className="space-y-2 rounded border border-white/15 bg-black/25 p-3">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">organizes</p>
            <p className="text-sm text-text/90">
              Five categories: transport, content, cookies, policy headers, cross-origin. One rule-based score plus optional ML estimate.
            </p>
          </div>
          <div className="space-y-2 rounded border border-white/15 bg-black/25 p-3">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">shows</p>
            <p className="text-sm text-text/90">
              Security profile (radar), recommendations with severity, and raw evidence.
            </p>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">story</h2>
        <p className="max-w-2xl text-sm text-muted">
          Security posture is visible in what your site sends. Outliner exists to surface that clearly: no guessing, no clutter. One scan, one report, so you can see where you stand and what to fix first.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">method</h2>
        <p className="max-w-2xl text-sm text-muted">
          We request your domain (following redirects), inspect the response, and score it with a transparent rule set (category-capped, 0–110). An optional ML model trained on prior scans adds a predicted score. Full detail—what we scan, how we score, what we don’t do—is on the method page.
        </p>
        <Link
          href="/method"
          className="inline-flex items-center text-xs text-red-500 underline-offset-4 hover:underline"
        >
          Full method →
        </Link>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">ethical use</h2>
        <p className="max-w-2xl text-sm text-muted">
          Run Outliner only on domains you own or have permission to test.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/#scan"
            className="inline-flex items-center rounded border border-red-500/60 bg-red-500/15 px-4 py-2 text-xs font-semibold tracking-wide text-red-500 transition hover:border-red-500 hover:bg-red-500/25"
          >
            RUN SCAN
          </Link>
        </div>
      </section>
    </div>
  )
}

