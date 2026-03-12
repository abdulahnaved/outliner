'use client'

type Props = {
  scanErrorType?: string | null
  scanErrorMessage?: string | null
}

export function PartialScanNotice({ scanErrorType, scanErrorMessage }: Props) {
  return (
    <section className="space-y-3 rounded border border-yellow-300/30 bg-yellow-300/5 p-4">
      <div className="space-y-1">
        <p className="text-[11px] uppercase tracking-[0.18em] text-yellow-200">partial scan</p>
        <p className="text-xs text-muted">
          The target responded, but we couldn&apos;t gather enough information for a full report.
        </p>
      </div>
      {(scanErrorType || scanErrorMessage) && (
        <div className="rounded border border-white/10 bg-black/15 p-3 text-xs text-muted">
          {scanErrorType ? <p>Type: {scanErrorType}</p> : null}
          {scanErrorMessage ? <p className="mt-1 break-words">Message: {scanErrorMessage}</p> : null}
        </div>
      )}
    </section>
  )
}

