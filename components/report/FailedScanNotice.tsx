'use client'

type Props = {
  scanErrorType?: string | null
  scanErrorMessage?: string | null
}

export function FailedScanNotice({ scanErrorType, scanErrorMessage }: Props) {
  return (
    <section className="space-y-3 rounded border border-red-400/30 bg-red-500/5 p-4">
      <div className="space-y-1">
        <p className="text-[11px] uppercase tracking-[0.18em] text-red-300">scan failed</p>
        <p className="text-xs text-muted">The scan could not be completed for this target.</p>
      </div>
      <div className="rounded border border-white/10 bg-black/15 p-3 text-xs text-muted">
        <p>Type: {scanErrorType || 'unknown'}</p>
        <p className="mt-1 break-words">Message: {scanErrorMessage || 'No additional details.'}</p>
      </div>
    </section>
  )
}

