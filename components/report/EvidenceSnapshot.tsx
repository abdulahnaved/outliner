'use client'

import type { ViewMode } from './ViewToggle'

type Props = {
  evidence?: Record<string, unknown> | null
  features?: Record<string, unknown> | null
  finalStatusCode?: number | null
  finalUrl?: string | null
  redirectCount?: number | null
  responseTime?: number | null
  viewMode: ViewMode
  highlightSection?: string | null
}

function isHighlighted(section: string, active: string | null | undefined): string {
  return active === section
    ? 'border-teal-500/50 shadow-[0_0_12px_rgba(45,212,191,0.08)]'
    : 'border-white/15'
}

export function EvidenceSnapshot({
  evidence,
  features,
  finalStatusCode,
  finalUrl,
  redirectCount,
  responseTime,
  viewMode,
  highlightSection
}: Props) {
  const tls = evidence && typeof evidence === 'object' ? (evidence as Record<string, unknown>) : null
  const headers = evidence && typeof evidence === 'object' ? (evidence as Record<string, unknown>) : null

  return (
    <div className="space-y-3">
      <div className="grid gap-3 lg:grid-cols-2">
        <div id="evidence-status" className={`space-y-2 rounded border bg-black/25 p-3 transition-colors duration-300 ${isHighlighted('status', highlightSection)}`}>
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">status</p>
          <div className="text-xs text-muted">
            <p>final status: {finalStatusCode ?? '\u2014'}</p>
            <p className="break-words">final url: {finalUrl ?? '\u2014'}</p>
            <p>redirects: {redirectCount ?? 0}</p>
            <p>response time: {typeof responseTime === 'number' ? `${responseTime}s` : '\u2014'}</p>
          </div>
        </div>

        <div id="evidence-tls" className={`space-y-2 rounded border bg-black/25 p-3 transition-colors duration-300 ${isHighlighted('tls', highlightSection)}`}>
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">tls</p>
          <pre className="overflow-x-auto whitespace-pre-wrap break-words bg-black/40 p-3 text-[11px] text-muted">
            {JSON.stringify(
              { tls_version_raw: tls?.tls_version_raw ?? null, cipher: tls?.cipher ?? null },
              null, 2
            )}
          </pre>
        </div>

        <div id="evidence-headers" className={`space-y-2 rounded border bg-black/25 p-3 lg:col-span-2 transition-colors duration-300 ${isHighlighted('headers', highlightSection)}`}>
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">selected headers</p>
          <pre className="overflow-x-auto whitespace-pre-wrap break-words bg-black/40 p-3 text-[11px] text-muted">
            {JSON.stringify(
              {
                hsts: headers?.hsts_raw ?? null,
                csp: headers?.csp_raw ?? null,
                x_frame: headers?.x_frame_value ?? null,
                x_content_type: headers?.x_content_type_value ?? null,
                referrer_policy: headers?.referrer_policy_raw ?? null,
                permissions_policy: headers?.permissions_policy_raw ?? null,
              },
              null, 2
            )}
          </pre>
        </div>

        {viewMode === 'technical' && (
          <div id="evidence-features" className={`space-y-2 rounded border bg-black/25 p-3 lg:col-span-2 transition-colors duration-300 ${isHighlighted('features', highlightSection)}`}>
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted">features (raw)</p>
            <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words bg-black/40 p-3 text-[11px] text-muted">
              {JSON.stringify(features ?? {}, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
