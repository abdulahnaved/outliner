'use client'

type Props = {
  target: string
  normalizedHost?: string | null
  timestamp: string
  status: 'success' | 'failed'
}

const badgeStyles: Record<Props['status'], string> = {
  success: 'border-teal-300/50 bg-teal-300/10 text-teal-200',
  failed: 'border-red-400/60 bg-red-500/10 text-red-300'
}

export function ReportHeader({ target, normalizedHost, timestamp, status }: Props) {
  return (
    <header className="space-y-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted">report</p>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold text-text">{target}</h1>
          {normalizedHost ? (
            <p className="text-[11px] text-muted">normalized host: {normalizedHost}</p>
          ) : null}
          <p className="text-xs text-muted">Generated at {timestamp}</p>
        </div>
        <span
          className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] ${badgeStyles[status]}`}
        >
          {status}
        </span>
      </div>
    </header>
  )
}

