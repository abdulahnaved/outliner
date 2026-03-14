import { evaluateRules, buildCategorySummaries } from './rules'
import type { ScanFeatures } from './rules'

describe('evaluateRules', () => {
  it('returns no issues when features are secure', () => {
    const features: ScanFeatures = {
      has_https: 1,
      has_hsts: 1,
      weak_tls: 0,
      has_csp: 1,
      total_cookie_count: 0,
      has_x_frame: 1,
      has_x_content_type: 1,
      has_referrer_policy: 1,
      referrer_policy_strict: 1,
      has_permissions_policy: 1,
      cors_wildcard_with_credentials: 0,
    }
    const issues = evaluateRules(features)
    expect(issues).toHaveLength(0)
  })

  it('flags missing HTTPS', () => {
    const features: ScanFeatures = { has_https: 0 }
    const issues = evaluateRules(features)
    const missing = issues.find((i) => i.id === 'missing_https')
    expect(missing).toBeDefined()
    expect(missing?.severity).toBe('HIGH')
  })

  it('flags HTTPS without HSTS', () => {
    const features: ScanFeatures = { has_https: 1, has_hsts: 0 }
    const issues = evaluateRules(features)
    const missing = issues.find((i) => i.id === 'missing_hsts')
    expect(missing).toBeDefined()
  })

  it('flags weak TLS', () => {
    const features: ScanFeatures = { has_https: 1, weak_tls: 1 }
    const issues = evaluateRules(features)
    const weak = issues.find((i) => i.id === 'weak_tls')
    expect(weak).toBeDefined()
    expect(weak?.severity).toBe('HIGH')
  })

  it('flags missing CSP', () => {
    const features: ScanFeatures = { has_csp: 0 }
    const issues = evaluateRules(features)
    const csp = issues.find((i) => i.id === 'missing_csp')
    expect(csp).toBeDefined()
  })

  it('handles empty or unknown features without throwing', () => {
    expect(() => evaluateRules({})).not.toThrow()
    const issues = evaluateRules({})
    expect(Array.isArray(issues)).toBe(true)
  })
})

describe('buildCategorySummaries', () => {
  it('returns all five categories', () => {
    const issues = evaluateRules({ has_https: 0 })
    const summaries = buildCategorySummaries(issues, { total_cookie_count: 0 })
    const categories = summaries.map((s) => s.category)
    expect(categories).toContain('transport_security')
    expect(categories).toContain('content_security')
    expect(categories).toContain('cookies')
    expect(categories).toContain('policy_headers')
    expect(categories).toContain('cross_origin')
    expect(summaries).toHaveLength(5)
  })

  it('marks cookies as Neutral when there are no cookies', () => {
    const issues = evaluateRules({ has_https: 1, total_cookie_count: 0 })
    const summaries = buildCategorySummaries(issues, { total_cookie_count: 0 })
    const cookies = summaries.find((s) => s.category === 'cookies')
    expect(cookies?.strength).toBe('Neutral')
    expect(cookies?.triggered).toHaveLength(0)
  })

  it('assigns Weak when a HIGH severity issue is in the category', () => {
    const issues = evaluateRules({ has_https: 0 })
    const summaries = buildCategorySummaries(issues, { total_cookie_count: 0 })
    const transport = summaries.find((s) => s.category === 'transport_security')
    expect(transport?.strength).toBe('Weak')
    expect(transport?.triggered.length).toBeGreaterThan(0)
  })
})
