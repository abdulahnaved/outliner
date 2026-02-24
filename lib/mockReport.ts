export const mockReport = {
  score: 78,
  grade: 'B',
  generatedAt: '2026-02-24T10:15:00Z',
  categories: [
    { name: 'Headers', pass: 6, warn: 2, fail: 1 },
    { name: 'TLS', pass: 4, warn: 1, fail: 1 },
    { name: 'Cookies', pass: 3, warn: 2, fail: 2 },
    { name: 'Content', pass: 5, warn: 1, fail: 1 }
  ],
  evidence: {
    headers: {
      server: 'nginx',
      'x-powered-by': 'hidden',
      'content-security-policy': 'present',
      'strict-transport-security': 'max-age=31536000; includeSubDomains; preload'
    },
    tls: {
      protocol: 'TLS 1.3',
      cipherSuite: 'TLS_AES_256_GCM_SHA384',
      certificateIssuer: 'Let’s Encrypt',
      expiresInDays: 63
    }
  },
  issues: [
    {
      id: 'hdr-missing-csp-report-uri',
      severity: 'MED',
      title: 'Content Security Policy has no reporting endpoint',
      category: 'Headers',
      evidence:
        'The Content-Security-Policy header is present, but no reporting or monitoring endpoint is configured.',
      fix: 'Add a report-uri or report-to directive to capture violations and watch for unexpected behavior.'
    },
    {
      id: 'cookie-missing-secure',
      severity: 'HIGH',
      title: 'A session-like cookie is not marked Secure',
      category: 'Cookies',
      evidence:
        'At least one cookie that appears to relate to sessions or authentication is sent without the Secure flag.',
      fix: 'Ensure all cookies that might carry sensitive context are marked Secure so they are only sent over HTTPS.'
    },
    {
      id: 'cookie-missing-samesite',
      severity: 'MED',
      title: 'Cookies missing SameSite attribute',
      category: 'Cookies',
      evidence:
        'Some cookies are sent without SameSite, which can increase the risk of cross-site request scenarios.',
      fix: 'Set SameSite=Lax or SameSite=Strict for cookies that do not need cross-site behavior.'
    },
    {
      id: 'tls-expiry-window',
      severity: 'LOW',
      title: 'TLS certificate within a typical renewal window',
      category: 'TLS',
      evidence:
        'The certificate expires in around two months. This is normal, but worth tracking in your renewal process.',
      fix: 'Make sure the certificate is renewed ahead of expiry and that alerts are in place for future renewals.'
    },
    {
      id: 'content-open-directories',
      severity: 'LOW',
      title: 'Some public paths behave like open indexes',
      category: 'Content',
      evidence:
        'At least one path returns a simple directory-style listing instead of a curated landing page.',
      fix: 'Replace index-like views with explicit pages or disable directory listings where not intentional.'
    }
  ]
} as const

export type MockReport = typeof mockReport

