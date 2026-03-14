type IssueCardProps = {
  title: string
  severity: 'LOW' | 'MED' | 'HIGH'
  category: string
  evidence: string
  fix: string
}

const severityStyles: Record<IssueCardProps['severity'], string> = {
  LOW: 'border-white/20 text-muted',
  MED: 'border-yellow-300/60 text-yellow-200',
  HIGH: 'border-red-400/70 text-red-300'
}

export function IssueCard({ title, severity, category, evidence, fix }: IssueCardProps) {
  return (
    <article className="space-y-2 rounded border border-white/15 bg-black/15 p-4">
      <header className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">{category}</p>
          <h3 className="mt-1 text-sm text-text">{title}</h3>
        </div>
        <span
          className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-wide ${severityStyles[severity]}`}
        >
          {severity}
        </span>
      </header>
      <p className="text-xs text-muted">{evidence}</p>
      <p className="text-xs text-text/90">{fix}</p>
    </article>
  )
}

