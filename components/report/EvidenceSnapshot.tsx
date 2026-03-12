'use client'

type Props = {
  evidence?: Record<string, unknown> | null
  features?: Record<string, unknown> | null
  finalStatusCode?: number | null
  finalUrl?: string | null
  redirectCount?: number | null
  responseTime?: number | null
}

export function EvidenceSnapshot({
  evidence,
  features,
  finalStatusCode,
  finalUrl,
  redirectCount,
  responseTime
}: Props) {
  const tls = evidence && typeof evidence === 'object' ? (evidence as any) : null
  const headers = evidence && typeof evidence === 'object' ? (evidence as any) : null

  return (
    <section className="space-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">evidence snapshot</h2>
      <div className="grid gap-3 lg:grid-cols-2">
        <div className="space-y-2 rounded border border-white/15 bg-black/25 p-3">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">status</p>
          <div className="text-xs text-muted">
            <p>final status: {finalStatusCode ?? '—'}</p>
            <p className="break-words">final url: {finalUrl ?? '—'}</p>
            <p>redirects: {redirectCount ?? 0}</p>
            <p>response time: {typeof responseTime === 'number' ? `${responseTime}s` : '—'}</p>
          </div>
        </div>

        <div className="space-y-2 rounded border border-white/15 bg-black/25 p-3">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">tls</p>
          <pre className="overflow-x-auto whitespace-pre-wrap break-words bg-black/40 p-3 text-[11px] text-muted">
            {JSON.stringify(
              {
                tls_version_raw: (tls as any)?.tls_version_raw ?? null,
                cipher: (tls as any)?.cipher ?? null
              },
              null,
              2
            )}
          </pre>
        </div>

        <div className="space-y-2 rounded border border-white/15 bg-black/25 p-3 lg:col-span-2">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">selected headers</p>
          <pre className="overflow-x-auto whitespace-pre-wrap break-words bg-black/40 p-3 text-[11px] text-muted">
            {JSON.stringify(
              {
                hsts: (headers as any)?.hsts_raw ?? null,
                csp: (headers as any)?.csp_raw ?? null,
                x_frame: (headers as any)?.x_frame_value ?? null,
                x_content_type: (headers as any)?.x_content_type_value ?? null,
                referrer_policy: (headers as any)?.referrer_policy_raw ?? null,
                permissions_policy: (headers as any)?.permissions_policy_raw ?? null
              },
              null,
              2
            )}
          </pre>
        </div>

        <div className="space-y-2 rounded border border-white/15 bg-black/25 p-3 lg:col-span-2">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">features (raw)</p>
          <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words bg-black/40 p-3 text-[11px] text-muted">
            {JSON.stringify(features ?? {}, null, 2)}
          </pre>
        </div>
      </div>
    </section>
  )
}

