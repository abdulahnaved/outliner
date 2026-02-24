import { Suspense } from 'react'
import { mockReport } from '../../../lib/mockReport'
import { ScoreCard } from '../../../components/ScoreCard'
import { IssueCard } from '../../../components/IssueCard'

function ReportInner({ searchParams }: { searchParams: { domain?: string } }) {
  const domain = searchParams.domain || 'demo.example'
  const { score, grade, generatedAt, categories, evidence, issues } = mockReport

  const generated = new Date(generatedAt)
  const timestamp = generated.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })

  return (
    <div className="space-y-10">
      <header className="space-y-2">
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted">report</p>
        <h1 className="text-2xl font-semibold text-text">{domain}</h1>
        <p className="text-xs text-muted">Generated at {timestamp}</p>
      </header>

      <ScoreCard score={score} grade={grade} />

      <section className="grid gap-6 lg:grid-cols-[2fr,3fr]">
        <div className="space-y-4">
          <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
            categories
          </h2>
          <div className="space-y-3">
            {categories.map((cat) => (
              <div
                key={cat.name}
                className="flex items-center justify-between rounded border border-white/15 bg-black/20 px-3 py-2 text-xs"
              >
                <div>
                  <p className="text-[11px] uppercase tracking-[0.18em] text-muted">
                    {cat.name}
                  </p>
                </div>
                <div className="flex gap-3 text-[11px] text-muted">
                  <span className="text-teal-300/80">pass {cat.pass}</span>
                  <span className="text-yellow-200/80">warn {cat.warn}</span>
                  <span className="text-red-300/80">fail {cat.fail}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
            evidence snapshot
          </h2>
          <div className="space-y-2 rounded border border-white/15 bg-black/25 p-3">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">headers</p>
            <pre className="overflow-x-auto whitespace-pre-wrap break-words bg-black/40 p-3 text-[11px] text-muted">
              {JSON.stringify(evidence.headers, null, 2)}
            </pre>
          </div>
          <div className="space-y-2 rounded border border-white/15 bg-black/25 p-3">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">tls</p>
            <pre className="overflow-x-auto whitespace-pre-wrap break-words bg-black/40 p-3 text-[11px] text-muted">
              {JSON.stringify(evidence.tls, null, 2)}
            </pre>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
          issues
        </h2>
        <div className="space-y-3">
          {issues.map((issue) => (
            <IssueCard
              key={issue.id}
              title={issue.title}
              severity={issue.severity as 'LOW' | 'MED' | 'HIGH'}
              category={issue.category}
              evidence={issue.evidence}
              fix={issue.fix}
            />
          ))}
        </div>
      </section>
    </div>
  )
}

export default function DemoReportPage(props: { searchParams: { domain?: string } }) {
  return (
    <Suspense fallback={<div className="text-xs text-muted">Loading report…</div>}>
      <ReportInner searchParams={props.searchParams} />
    </Suspense>
  )
}

