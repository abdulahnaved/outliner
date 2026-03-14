'use client'

/**
 * Feature importances from gradient_boosting_regressor (actual model values).
 * We show a subset that varies by site relevance and use a soft scale for bar length
 * so the chart isn’t dominated by one bar (reality: top 2 are ~29% and ~24%, rest 4–5%).
 */
const ALL_FEATURES: { key: string; label: string; value: number }[] = [
  { key: 'hsts_max_age', label: 'HSTS strength', value: 0.292 },
  { key: 'total_cookie_count', label: 'Cookie configuration', value: 0.239 },
  { key: 'has_referrer_policy', label: 'Referrer-Policy', value: 0.052 },
  { key: 'has_csp', label: 'CSP presence', value: 0.044 },
  { key: 'secure_cookie_ratio', label: 'Secure cookie ratio', value: 0.049 },
  { key: 'httponly_cookie_ratio', label: 'HttpOnly cookie ratio', value: 0.038 },
  { key: 'redirect_http_to_https', label: 'HTTP → HTTPS redirect', value: 0.033 },
  { key: 'has_permissions_policy', label: 'Permissions-Policy', value: 0.033 },
  { key: 'tls_version', label: 'TLS version', value: 0.04 },
  { key: 'csp_unsafe_eval', label: 'CSP unsafe-eval', value: 0.037 }
]

/** Power scale to compress bar lengths so differences are visible but not stark. */
const BAR_POWER = 0.45

type Props = {
  /** Percentile of current score in dataset (0–100). Used for confidence. */
  percentile?: number | null
  predictionAvailable?: boolean
  /** Optional scan features: when present, we pick/order features by relevance to this site. */
  features?: Record<string, unknown>
}

function confidenceFromPercentile(pct: number | null | undefined): 'High' | 'Medium' | 'Low' | null {
  if (pct == null || Number.isNaN(pct)) return null
  if (pct >= 25 && pct <= 75) return 'High'
  if (pct >= 10 && pct < 25) return 'Medium'
  if (pct > 75 && pct <= 90) return 'Medium'
  return 'Low'
}

function num(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

/** Pick and order top N features; when features exist, boost relevance for weak/missing so the list varies by site. */
function pickFeaturesForDisplay(
  features: Record<string, unknown> | undefined,
  count: number
): { label: string; value: number; sharePct: number }[] {
  const withRelevance = ALL_FEATURES.map((f) => {
    let relevance = f.value
    if (features) {
      const v = features[f.key]
      if (f.key === 'has_hsts' || f.key === 'hsts_max_age') {
        if (num(features.has_hsts) === 0) relevance *= 1.4
      } else if (f.key === 'has_csp') {
        if (num(v) === 0) relevance *= 1.3
      } else if (f.key === 'secure_cookie_ratio' || f.key === 'httponly_cookie_ratio') {
        if (num(v) < 1 && num(features.total_cookie_count) > 0) relevance *= 1.2
      } else if (f.key === 'redirect_http_to_https') {
        if (num(v) === 0) relevance *= 1.2
      } else if (f.key === 'has_referrer_policy' || f.key === 'has_permissions_policy') {
        if (num(v) === 0) relevance *= 1.15
      }
    }
    return { ...f, relevance }
  })
  withRelevance.sort((a, b) => b.relevance - a.relevance)
  const selected = withRelevance.slice(0, count)
  return selected.map((f) => ({
    label: f.label,
    value: f.value,
    sharePct: Math.round(f.value * 100)
  }))
}

export function ModelInsight({
  percentile,
  predictionAvailable,
  features
}: Props) {
  const confidence = confidenceFromPercentile(percentile ?? undefined)
  const displayFeatures = pickFeaturesForDisplay(features, 6)
  const maxVal = Math.max(...displayFeatures.map((f) => f.value))

  return (
    <section className="space-y-5 rounded border border-white/15 bg-black/20 p-4">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted">model insight</p>

      {/* Feature contribution – horizontal bar chart (soft scale so no single bar dominates) */}
      <div className="space-y-2">
        <p className="text-xs text-muted">
          What drives the ML estimate (ordered by relevance to this site)
        </p>
        <div className="space-y-2.5">
          {displayFeatures.map(({ label, value, sharePct }) => {
            const softRatio = maxVal > 0 ? Math.pow(value / maxVal, BAR_POWER) : 0
            const widthPct = Math.round(softRatio * 100)
            return (
              <div key={label} className="flex items-center gap-3">
                <span className="w-36 shrink-0 text-[11px] text-muted">{label}</span>
                <div className="min-w-0 flex-1 rounded-full bg-white/10">
                  <div
                    className="h-2 rounded-full bg-teal-400/70 transition-all duration-500"
                    style={{ width: `${widthPct}%` }}
                    role="presentation"
                  />
                </div>
                <span className="w-8 shrink-0 text-right text-[10px] text-muted tabular-nums">
                  {sharePct}%
                </span>
              </div>
            )
          })}
        </div>
        <p className="text-[10px] text-muted/80">
          Bar length uses a soft scale; number is each factor’s share of total model importance.
        </p>
      </div>

      {/* Prediction confidence */}
      {predictionAvailable && (
        <div className="rounded border border-white/10 bg-black/15 px-3 py-2.5">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">
            Prediction confidence
          </p>
          <p className="mt-1 text-sm font-medium text-text">
            {confidence == null ? (
              '—'
            ) : (
              <>
                <span
                  className={
                    confidence === 'High'
                      ? 'text-teal-300'
                      : confidence === 'Medium'
                        ? 'text-yellow-200'
                        : 'text-amber-300'
                  }
                >
                  {confidence}
                </span>
              </>
            )}
          </p>
          <p className="mt-0.5 text-[11px] text-muted">
            {confidence != null
              ? 'Based on similarity to previously scanned configurations.'
              : 'Percentile not available for this scan.'}
          </p>
        </div>
      )}
    </section>
  )
}
