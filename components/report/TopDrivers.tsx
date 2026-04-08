'use client'

import { useState } from 'react'
import type { Issue, RuleCategory } from '../../lib/rules'
import type { ViewMode } from './ViewToggle'

type Driver = {
  id: string
  label: string
  shortLabel: string
  sentiment: 'positive' | 'negative' | 'neutral'
  category: RuleCategory
  beginner: string
  technical: string
}

function num(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

function deriveDrivers(features: Record<string, unknown>, issues: Issue[]): Driver[] {
  const drivers: Driver[] = []

  if (num(features.has_https) === 1) {
    drivers.push({
      id: 'https_on', label: 'HTTPS enabled', shortLabel: 'HTTPS', sentiment: 'positive',
      category: 'transport_security',
      beginner: 'The site uses encrypted HTTPS, so connections are private.',
      technical: 'TLS-encrypted transport detected; has_https=1.'
    })
  } else {
    drivers.push({
      id: 'https_off', label: 'No HTTPS', shortLabel: 'No HTTPS', sentiment: 'negative',
      category: 'transport_security',
      beginner: 'The site does not use HTTPS. All traffic is exposed.',
      technical: 'has_https=0. Major transport penalty applied.'
    })
  }

  if (num(features.has_hsts) === 0 && num(features.has_https) === 1) {
    drivers.push({
      id: 'hsts_missing', label: 'HSTS missing', shortLabel: 'No HSTS', sentiment: 'negative',
      category: 'transport_security',
      beginner: 'The server doesn\u2019t tell browsers to always use HTTPS.',
      technical: 'Strict-Transport-Security header absent; transport penalty.'
    })
  } else if (num(features.has_hsts) === 1) {
    drivers.push({
      id: 'hsts_on', label: 'HSTS enabled', shortLabel: 'HSTS', sentiment: 'positive',
      category: 'transport_security',
      beginner: 'Browsers are told to always use HTTPS for this site.',
      technical: 'HSTS header present; hsts_long=' + num(features.hsts_long) + '.'
    })
  }

  if (num(features.has_csp) === 0) {
    drivers.push({
      id: 'csp_missing', label: 'CSP not set', shortLabel: 'No CSP', sentiment: 'negative',
      category: 'content_security',
      beginner: 'No Content-Security-Policy header. The browser has no restrictions on what scripts run.',
      technical: 'has_csp=0; content penalty.'
    })
  } else {
    const score = num(features.csp_score)
    drivers.push({
      id: 'csp_on', label: score >= 0.7 ? 'Strong CSP' : 'CSP present (weak)', shortLabel: 'CSP', sentiment: score >= 0.7 ? 'positive' : 'neutral',
      category: 'content_security',
      beginner: score >= 0.7 ? 'A strong content policy limits what the page can load.' : 'A content policy exists but has gaps (e.g. unsafe-inline).',
      technical: `csp_score=${score.toFixed(2)}; unsafe_inline=${num(features.csp_unsafe_inline)}, unsafe_eval=${num(features.csp_unsafe_eval)}.`
    })
  }

  if (num(features.weak_tls) === 1) {
    drivers.push({
      id: 'weak_tls', label: 'Weak TLS', shortLabel: 'Weak TLS', sentiment: 'negative',
      category: 'transport_security',
      beginner: 'The encryption version is outdated, making connections easier to attack.',
      technical: 'weak_tls=1; TLS version < 1.2 or weak cipher detected.'
    })
  }

  if (num(features.has_referrer_policy) === 0) {
    drivers.push({
      id: 'rp_missing', label: 'Referrer-Policy missing', shortLabel: 'No Referrer-Policy', sentiment: 'negative',
      category: 'policy_headers',
      beginner: 'The site leaks the full page URL to other sites when users click links.',
      technical: 'has_referrer_policy=0; browser policy penalty.'
    })
  }

  if (num(features.has_permissions_policy) === 0) {
    drivers.push({
      id: 'pp_missing', label: 'Permissions-Policy missing', shortLabel: 'No Permissions-Policy', sentiment: 'negative',
      category: 'policy_headers',
      beginner: 'The site hasn\u2019t restricted which browser features (camera, microphone, etc.) it can use.',
      technical: 'has_permissions_policy=0; policy header penalty.'
    })
  }

  if (num(features.total_cookie_count) > 0) {
    const sr = num(features.secure_cookie_ratio)
    if (sr < 1) {
      drivers.push({
        id: 'cookie_insecure', label: 'Insecure cookies', shortLabel: 'Cookies', sentiment: 'negative',
        category: 'cookies',
        beginner: 'Some cookies are not marked Secure, so they could be sent over unencrypted connections.',
        technical: `secure_cookie_ratio=${sr.toFixed(2)}; cookie penalty.`
      })
    }
  }

  if (num(features.cors_wildcard_with_credentials) === 1) {
    drivers.push({
      id: 'cors_bad', label: 'CORS wildcard + credentials', shortLabel: 'CORS risk', sentiment: 'negative',
      category: 'cross_origin',
      beginner: 'The site allows any website to read its data with user credentials \u2014 a serious misconfiguration.',
      technical: 'cors_wildcard_with_credentials=1; cross-origin penalty.'
    })
  }

  return drivers.slice(0, 6)
}

const sentimentStyles = {
  positive: 'border-teal-500/40 bg-teal-500/10 text-teal-300 hover:border-teal-400/60',
  negative: 'border-red-500/40 bg-red-500/10 text-red-300 hover:border-red-400/60',
  neutral: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-200 hover:border-yellow-400/60'
}

type Props = {
  features: Record<string, unknown>
  issues: Issue[]
  viewMode: ViewMode
  onCategoryClick?: (cat: RuleCategory) => void
}

export function TopDrivers({ features, issues, viewMode, onCategoryClick }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null)
  const drivers = deriveDrivers(features, issues)
  if (drivers.length === 0) return null

  return (
    <section className="space-y-3 rounded border border-white/15 bg-black/20 p-4">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted">
        {viewMode === 'beginner' ? 'why this score?' : 'top drivers'}
      </p>
      <p className="text-[11px] text-muted">
        {viewMode === 'beginner'
          ? 'The main things that helped or hurt this site\u2019s security score.'
          : 'Key feature signals contributing to the rule-based assessment.'}
      </p>
      <div className="flex flex-wrap gap-2">
        {drivers.map((d) => (
          <button
            key={d.id}
            type="button"
            onClick={() => setExpanded(expanded === d.id ? null : d.id)}
            className={`rounded-full border px-3 py-1 text-[11px] font-medium transition-colors ${sentimentStyles[d.sentiment]} ${expanded === d.id ? 'ring-1 ring-white/20' : ''}`}
          >
            {d.sentiment === 'positive' ? '\u2713 ' : d.sentiment === 'negative' ? '\u2717 ' : '\u25CB '}
            {d.shortLabel}
          </button>
        ))}
      </div>
      {expanded && (() => {
        const d = drivers.find((dr) => dr.id === expanded)
        if (!d) return null
        return (
          <div className="rounded border border-white/10 bg-black/25 p-3 text-xs">
            <p className="font-medium text-text/90">{d.label}</p>
            <p className="mt-1 text-muted">{viewMode === 'beginner' ? d.beginner : d.technical}</p>
            <button
              type="button"
              className="mt-2 text-[10px] text-teal-400/80 underline underline-offset-2 hover:text-teal-300"
              onClick={() => onCategoryClick?.(d.category)}
            >
              Jump to {d.category.replaceAll('_', ' ')} \u2192
            </button>
          </div>
        )
      })()}
    </section>
  )
}
