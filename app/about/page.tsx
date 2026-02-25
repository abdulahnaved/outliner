import Link from 'next/link'

export default function AboutPage() {
  return (
    <div className="space-y-24">
      <section className="space-y-6">
        <div className="space-y-3">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold sm:text-4xl">what it is</h1>
            <p className="max-w-xl text-sm text-muted">
              Outliner is a calm surface over noisy public signals. It doesn&apos;t guess at intent;
              it simply lines up what your website is already saying.
            </p>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-2 rounded border border-white/15 bg-black/25 p-3">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">reads</p>
            <p className="text-sm text-text/90">
              Looks at headers, TLS details, cookies, and simple content signals.
            </p>
          </div>
          <div className="space-y-2 rounded border border-white/15 bg-black/25 p-3">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">organizes</p>
            <p className="text-sm text-text/90">
              Groups findings into clear categories with a single synthetic score.
            </p>
          </div>
          <div className="space-y-2 rounded border border-white/15 bg-black/25 p-3">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">shows</p>
            <p className="text-sm text-text/90">
              Pairs every highlight with a short explanation and suggested next step.
            </p>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">
          current state
        </h2>
        <div className="space-y-3 text-sm text-muted">
          <p>This is a static UI. The real scanner and data pipeline come later.</p>
          <p>
            For now, the demo report is a fixed example designed to show how scores,
            categories, and issues might be laid out.
          </p>
          <p className="text-[11px] text-muted/80">
            Ethical use only: outliner is meant for your own domains or places where you have clear
            permission to test.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/#scan"
            className="inline-flex items-center rounded border border-brandRed/60 bg-brandRed/15 px-4 py-2 text-xs font-semibold tracking-wide text-brandRed shadow-glow transition hover:border-brandRed hover:bg-brandRed/25"
          >
            RUN SCAN
          </Link>
          <Link
            href="/report/demo"
            className="inline-flex items-center text-xs text-accent underline-offset-4 hover:underline"
          >
            Open demo report
          </Link>
        </div>
      </section>
    </div>
  )
}

