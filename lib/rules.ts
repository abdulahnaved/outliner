export type Severity = 'LOW' | 'MED' | 'HIGH'

export type RuleCategory =
  | 'transport_security'
  | 'content_security'
  | 'cookies'
  | 'policy_headers'
  | 'cross_origin'

export type ScanFeatures = Record<string, unknown>

export type Rule = {
  id: string
  title: string
  category: RuleCategory
  severity: Severity
  description: string
  recommendation: string
  condition: (features: ScanFeatures) => boolean
  /**
   * Optional dedupe key: if multiple rules share a key and are triggered,
   * they will be merged into a single issue.
   */
  dedupeKey?: string
}

export type Issue = {
  id: string
  title: string
  category: RuleCategory
  severity: Severity
  description: string
  recommendation: string
}

export type CategorySummaryStrength = 'Strong' | 'Moderate' | 'Weak' | 'Neutral'

export type CategorySummary = {
  category: RuleCategory
  title: string
  strength: CategorySummaryStrength
  triggered: Issue[]
}

function num(v: unknown, fallback = 0) {
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}

function isOn(v: unknown) {
  return num(v) === 1
}

const severityRank: Record<Severity, number> = { HIGH: 3, MED: 2, LOW: 1 }

function maxSeverity(a: Severity, b: Severity): Severity {
  return severityRank[a] >= severityRank[b] ? a : b
}

function strengthFromIssues(issues: Issue[]): CategorySummaryStrength {
  if (issues.length === 0) return 'Strong'
  if (issues.some((i) => i.severity === 'HIGH')) return 'Weak'
  if (issues.some((i) => i.severity === 'MED')) return 'Moderate'
  return 'Strong'
}

export const RULES: Rule[] = [
  // Transport
  {
    id: 'missing_https',
    title: 'HTTPS not detected',
    category: 'transport_security',
    severity: 'HIGH',
    description: 'The site does not appear to support HTTPS, exposing traffic to interception.',
    recommendation: 'Enable HTTPS and redirect all HTTP traffic to HTTPS.',
    condition: (f) => !isOn(f.has_https)
  },
  {
    id: 'missing_hsts',
    title: 'HTTPS enabled but HSTS missing',
    category: 'transport_security',
    severity: 'MED',
    description: 'The site supports HTTPS but does not enforce HSTS.',
    recommendation: 'Add Strict-Transport-Security with max-age >= 6 months and includeSubDomains if safe.',
    condition: (f) => isOn(f.has_https) && !isOn(f.has_hsts)
  },
  {
    id: 'weak_tls',
    title: 'Weak TLS configuration detected',
    category: 'transport_security',
    severity: 'HIGH',
    description: 'The TLS setup indicates an outdated protocol or weak cipher signal.',
    recommendation: 'Disable legacy TLS versions and weak ciphers; prefer TLS 1.2+ and modern cipher suites.',
    condition: (f) => isOn(f.has_https) && isOn(f.weak_tls)
  },
  {
    id: 'cert_expired',
    title: 'TLS certificate expired or invalid',
    category: 'transport_security',
    severity: 'HIGH',
    description: 'The certificate is expired or appears invalid for this host.',
    recommendation: 'Renew the certificate and ensure correct hostname/SAN configuration.',
    condition: (f) => {
      const days = num(f.certificate_days_left, Number.POSITIVE_INFINITY)
      return isOn(f.has_https) && Number.isFinite(days) && days <= 0
    }
  },

  // Content security
  {
    id: 'missing_csp',
    title: 'Content Security Policy missing',
    category: 'content_security',
    severity: 'MED',
    description: 'No Content-Security-Policy header was detected.',
    recommendation: 'Add a restrictive CSP (start with default-src \'self\') and iterate with reporting.',
    condition: (f) => !isOn(f.has_csp)
  },
  {
    id: 'csp_unsafe_inline',
    title: 'CSP allows unsafe-inline',
    category: 'content_security',
    severity: 'MED',
    description: 'The CSP includes \'unsafe-inline\', increasing XSS risk.',
    recommendation: 'Remove unsafe-inline by using nonces/hashes and moving inline scripts/styles to external files.',
    condition: (f) => isOn(f.has_csp) && isOn(f.csp_unsafe_inline)
  },
  {
    id: 'csp_unsafe_eval',
    title: 'CSP allows unsafe-eval',
    category: 'content_security',
    severity: 'MED',
    description: 'The CSP includes \'unsafe-eval\', which can enable dangerous code execution paths.',
    recommendation: 'Remove unsafe-eval by avoiding eval-like patterns and using safer libraries/configurations.',
    condition: (f) => isOn(f.has_csp) && isOn(f.csp_unsafe_eval)
  },

  // Cookies (explicit rules requested)
  {
    id: 'cookies_insecure',
    title: 'Cookies missing Secure attribute',
    category: 'cookies',
    severity: 'HIGH',
    description: 'Not all cookies are marked Secure, so they may be sent over HTTP.',
    recommendation: 'Mark all cookies that carry sensitive context as Secure and serve them only over HTTPS.',
    condition: (f) => num(f.total_cookie_count) > 0 && num(f.secure_cookie_ratio, 1) < 1
  },
  {
    id: 'cookies_missing_httponly',
    title: 'Cookies missing HttpOnly attribute',
    category: 'cookies',
    severity: 'MED',
    description: 'Not all cookies are marked HttpOnly, so they may be readable by JavaScript.',
    recommendation: 'Mark session/auth cookies as HttpOnly to reduce exposure to XSS.',
    condition: (f) => num(f.total_cookie_count) > 0 && num(f.httponly_cookie_ratio, 1) < 1
  },
  {
    id: 'cookies_missing_samesite',
    title: 'Cookies missing SameSite attribute',
    category: 'cookies',
    severity: 'MED',
    description: 'Not all cookies have a SameSite attribute, increasing cross-site request risk.',
    recommendation: 'Set SameSite=Lax (or Strict where possible) for cookies that do not require cross-site behavior.',
    condition: (f) => num(f.total_cookie_count) > 0 && num(f.samesite_cookie_ratio, 1) < 1
  },

  // Policy headers (dedupe referrer-policy missing/weak)
  {
    id: 'referrer_policy_missing',
    title: 'Referrer-Policy missing or weak',
    category: 'policy_headers',
    severity: 'MED',
    description: 'A strict Referrer-Policy reduces unnecessary leakage of URL information.',
    recommendation: 'Set Referrer-Policy to strict-origin-when-cross-origin or no-referrer.',
    condition: (f) => !isOn(f.has_referrer_policy) || !isOn(f.referrer_policy_strict),
    dedupeKey: 'referrer_policy'
  },
  {
    id: 'permissions_policy_missing',
    title: 'Permissions-Policy missing',
    category: 'policy_headers',
    severity: 'LOW',
    description: 'Permissions-Policy helps restrict powerful browser features.',
    recommendation: 'Add a Permissions-Policy to limit features to what the site actually needs.',
    condition: (f) => !isOn(f.has_permissions_policy)
  },

  // Cross-origin controls
  {
    id: 'cors_wildcard_with_credentials',
    title: 'CORS wildcard with credentials',
    category: 'cross_origin',
    severity: 'HIGH',
    description: 'Allowing credentials with permissive origins can enable cross-origin data access.',
    recommendation: 'Avoid wildcard origins when credentials are allowed; use explicit allowlists.',
    condition: (f) => isOn(f.cors_wildcard_with_credentials)
  }
]

export function evaluateRules(features: ScanFeatures): Issue[] {
  const triggered = RULES.filter((r) => {
    try {
      return r.condition(features)
    } catch {
      return false
    }
  }).map<Issue>((r) => ({
    id: r.id,
    title: r.title,
    category: r.category,
    severity: r.severity,
    description: r.description,
    recommendation: r.recommendation
  }))

  // Dedupe/merge: by dedupeKey if present, else by id
  const merged = new Map<string, Issue>()
  for (const rule of RULES) {
    const issue = triggered.find((t) => t.id === rule.id)
    if (!issue) continue
    const key = rule.dedupeKey || issue.id
    const existing = merged.get(key)
    if (!existing) {
      merged.set(key, issue)
      continue
    }
    merged.set(key, {
      ...existing,
      severity: maxSeverity(existing.severity, issue.severity)
    })
  }

  const out = [...merged.values()]
  out.sort((a, b) => severityRank[b.severity] - severityRank[a.severity])
  return out
}

export function buildCategorySummaries(issues: Issue[], features: ScanFeatures): CategorySummary[] {
  const defs: { category: RuleCategory; title: string }[] = [
    { category: 'transport_security', title: 'Transport Security' },
    { category: 'content_security', title: 'Content Security' },
    { category: 'cookies', title: 'Cookies' },
    { category: 'policy_headers', title: 'Browser / Policy Headers' },
    { category: 'cross_origin', title: 'Cross-Origin Controls' }
  ]

  const totalCookies = num(features.total_cookie_count, 0)

  return defs.map((d) => {
    const triggered = issues.filter((i) => i.category === d.category)

    // Special-case cookies: no cookies => Neutral (no issues)
    if (d.category === 'cookies' && totalCookies === 0) {
      return {
        category: d.category,
        title: d.title,
        strength: 'Neutral' as CategorySummaryStrength,
        triggered: []
      }
    }

    return {
      category: d.category,
      title: d.title,
      strength: strengthFromIssues(triggered),
      triggered
    }
  })
}

