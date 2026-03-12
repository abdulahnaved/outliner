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
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">run a dummy scan</p>
            <p className="text-xs text-muted">
              This is a static demo. We&apos;ll show a pre-baked report using the domain you enter.
            </p>
          </div>
          <DomainInput />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">preview</h2>
        <div className="grid gap-6 rounded border border-white/15 bg-black/25 p-4 sm:grid-cols-[2fr,3fr]">
          <div className="space-y-3">
            <div>
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted">overall</p>
              <div className="mt-1 flex items-baseline gap-3">
                <span className="text-3xl font-semibold tabular-nums">78</span>
                <span className="rounded border border-white/15 px-2 py-0.5 text-xs text-muted">
                  grade B
                </span>
              </div>
            </div>
            <div className="h-1.5 w-full rounded-full bg-white/5">
              <div className="h-full w-[78%] rounded-full bg-accent shadow-glow" />
            </div>
          </div>
          <div className="grid gap-2 text-xs text-muted sm:grid-cols-2">
            <div className="space-y-1 rounded border border-white/10 bg-black/20 p-3">
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted">Headers</p>
              <p>6 pass / 2 warn / 1 fail</p>
            </div>
            <div className="space-y-1 rounded border border-white/10 bg-black/20 p-3">
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted">TLS</p>
              <p>4 pass / 1 warn / 1 fail</p>
            </div>
            <div className="space-y-1 rounded border border-white/10 bg-black/20 p-3">
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted">Cookies</p>
              <p>3 pass / 2 warn / 2 fail</p>
            </div>
            <div className="space-y-1 rounded border border-white/10 bg-black/20 p-3">
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted">Content</p>
              <p>5 pass / 1 warn / 1 fail</p>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/report/demo"
            className="inline-flex items-center rounded border border-accent/60 bg-accent/15 px-4 py-2 text-xs font-semibold tracking-wide text-accent shadow-glow transition hover:border-accent hover:bg-accent/20"
          >
            OPEN DEMO REPORT
          </Link>
          <Link
            href="/#scan"
            className="inline-flex items-center text-xs text-red-500 underline-offset-4 hover:underline"
          >
            Run scan
          </Link>
        </div>
      </section>

      <section id="method" className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">method</h2>
        <div className="space-y-3 text-sm text-muted">
          <p>Outliner looks at what&apos;s publicly visible and summarizes it.</p>
          <p>This is a static demo UI; the scanner comes later.</p>
          <p className="text-[11px] text-muted/80">
            Ethical use only: run it on domains you own or have permission to test.
          </p>
        </div>
      </section>

      <section id="contact" className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted">contact</h2>
        <div className="space-y-2 text-sm text-muted">
          <p>Say hello: contact@outlinerdemo (static placeholder)</p>
        </div>
        <Link
          href="/#scan"
          className="inline-flex items-center text-xs text-accent underline-offset-4 hover:underline"
        >
          Back to top
        </Link>
      </section>
    </div>
  )
}

