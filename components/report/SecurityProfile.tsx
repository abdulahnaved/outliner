'use client'

import { useRef, useState } from 'react'
import type { Issue, RuleCategory } from '../../lib/rules'
import type { ViewMode } from './ViewToggle'

type Strength = 'Strong' | 'Moderate' | 'Weak' | 'Neutral'

const AXIS_INTEL = [
  {
    short: 'Transport',
    category: 'transport_security' as RuleCategory,
    signal: 'SIGMA-1 // ENVELOPE',
    what: 'Encrypted tunnels & forced HTTPS',
    beginner: 'This checks whether the connection between you and the website is encrypted and safe from eavesdropping.',
    technical: 'Evaluates HTTPS availability, HTTP\u2192HTTPS redirects, HSTS header presence/strength, TLS version, and certificate validity.'
  },
  {
    short: 'Content',
    category: 'content_security' as RuleCategory,
    signal: 'SIGMA-2 // SANDBOX',
    what: 'What the page is allowed to load & run',
    beginner: 'This checks whether the site tells browsers which scripts and resources are allowed to run, to prevent attacks.',
    technical: 'Assesses Content-Security-Policy header: default-src, script-src directives, unsafe-inline/eval usage, wildcard presence.'
  },
  {
    short: 'Cookies',
    category: 'cookies' as RuleCategory,
    signal: 'SIGMA-3 // SESSION TOKENS',
    what: 'How login & session cookies are guarded',
    beginner: 'Cookies store your login information. This checks if they\u2019re protected from being stolen.',
    technical: 'Inspects Set-Cookie flags: Secure, HttpOnly, SameSite attributes and their ratios across all cookies.'
  },
  {
    short: 'Policy',
    category: 'policy_headers' as RuleCategory,
    signal: 'SIGMA-4 // BROWSER DIRECTIVES',
    what: 'Extra headers that steer browser behavior',
    beginner: 'Extra instructions the site gives to your browser \u2014 like not leaking URLs and blocking clickjacking.',
    technical: 'Checks Referrer-Policy, Permissions-Policy, X-Frame-Options, X-Content-Type-Options header presence and values.'
  },
  {
    short: 'Cross-Origin',
    category: 'cross_origin' as RuleCategory,
    signal: 'SIGMA-5 // PERIMETER',
    what: 'Who else can read this site\u2019s data',
    beginner: 'Controls which other websites can access this site\u2019s data. Bad settings can let attackers read sensitive info.',
    technical: 'Evaluates CORS (Access-Control-Allow-Origin / Credentials), COOP, COEP, and CORP isolation headers.'
  }
] as const

const STRENGTH_TO_SCORE: Record<Strength, number> = { Strong: 90, Moderate: 60, Weak: 30, Neutral: 50 }
const STRENGTH_COLOR: Record<Strength, string> = {
  Strong: 'text-teal-300', Moderate: 'text-yellow-200', Weak: 'text-red-300', Neutral: 'text-blue-300'
}

const CATEGORY_ORDER = [
  'Transport Security', 'Content Security', 'Cookies', 'Browser / Policy Headers', 'Cross-Origin Controls'
] as const

type Props = {
  categories: { title: string; strength: Strength }[]
  issues: Issue[]
  viewMode: ViewMode
}

function getScore(strength: Strength): number {
  return STRENGTH_TO_SCORE[strength] ?? 50
}

function getInterpretation(categories: { title: string; strength: Strength; score: number }[]): string {
  const sorted = [...categories].sort((a, b) => a.score - b.score)
  const lowest = sorted[0]
  if (!lowest) return 'Security posture across categories.'
  const lowestScore = lowest.score
  const weak = sorted.filter((c) => c.score === lowestScore)
  const names = weak.map((c) => c.title.toLowerCase())
  if (weak.length === 0) return 'Strong overall posture.'
  if (weak.length === 1) {
    if (lowestScore >= 80) return 'Strong overall posture with minor variation across categories.'
    if (lowestScore >= 50) return `Overall posture is mixed; the main gap is in ${names[0]}.`
    return `Security posture is uneven, with the main weakness in ${names[0]}.`
  }
  if (weak.length === 2) {
    if (lowestScore >= 50) return `Overall posture is mixed, with gaps in ${names[0]} and ${names[1]}.`
    return `Security posture is uneven, with weaknesses in ${names[0]} and ${names[1]}.`
  }
  return 'Security posture is uneven, with weaknesses concentrated in several areas.'
}

export function SecurityProfile({ categories, issues, viewMode }: Props) {
  const [hoverAxis, setHoverAxis] = useState<number | null>(null)
  const [selectedAxis, setSelectedAxis] = useState<number | null>(null)
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 })
  const containerRef = useRef<HTMLDivElement>(null)

  const byTitle = new Map(categories.map((c) => [c.title, c]))
  const ordered = CATEGORY_ORDER.map((title) => {
    const cat = byTitle.get(title)
    const strength = cat?.strength ?? 'Neutral'
    return { title, strength, score: getScore(strength) }
  })
  const interpretation = getInterpretation(ordered)

  const size = 440, cx = size / 2, cy = size / 2, radius = 115, labelR = radius + 38, n = 5
  const angles = Array.from({ length: n }, (_, i) => (90 - i * 72) * (Math.PI / 180))
  const axisLabels = ['Transport', 'Content', 'Cookies', 'Policy', 'Cross-Origin']

  const axisEndPoints = angles.map((a) => ({ x: cx + radius * Math.cos(a), y: cy - radius * Math.sin(a) }))
  const dataPoints = ordered.map((d, i) => {
    const r = radius * (d.score / 100)
    const a = angles[i]
    return { x: cx + r * Math.cos(a), y: cy - r * Math.sin(a) }
  })
  const polygonPoints = dataPoints.map((p) => `${p.x},${p.y}`).join(' ')

  const handleAxisEnter = (i: number, e: React.MouseEvent<SVGGElement>) => {
    const svg = e.currentTarget.closest('svg')
    const container = containerRef.current
    if (!svg || !container) return
    const svgRect = svg.getBoundingClientRect()
    const containerRect = container.getBoundingClientRect()
    const a = angles[i]
    const lx = cx + labelR * Math.cos(a)
    const ly = cy - labelR * Math.sin(a)
    const scaleX = svgRect.width / size
    const scaleY = svgRect.height / size
    setTooltipPos({
      x: svgRect.left + lx * scaleX - containerRect.left,
      y: svgRect.top + ly * scaleY - containerRect.top
    })
    setHoverAxis(i)
  }

  const activeIdx = hoverAxis ?? selectedAxis
  const catIssues = selectedAxis !== null
    ? issues.filter((i) => i.category === AXIS_INTEL[selectedAxis].category)
    : []

  return (
    <div className="space-y-4">
      <p className="text-[11px] text-muted">
        {viewMode === 'beginner'
          ? 'Click an axis to see what it means and what we found.'
          : 'Click an axis for category detail. Hover for quick intel.'}
      </p>

      <div ref={containerRef} className="relative flex flex-col items-center">
        <svg
          viewBox={`0 0 ${size} ${size}`}
          className="h-[min(90vw,400px)] w-[min(90vw,400px)] max-w-full text-muted"
          role="img"
          aria-label="Security posture radar chart with five axes."
        >
          {[25, 50, 75].map((pct) => {
            const r = radius * (pct / 100)
            const pts = angles.map((a) => `${cx + r * Math.cos(a)},${cy - r * Math.sin(a)}`).join(' ')
            return <polygon key={pct} points={pts} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
          })}
          {axisEndPoints.map((p, i) => (
            <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
          ))}
          <polygon points={polygonPoints} fill="rgba(45, 212, 191, 0.15)" stroke="rgba(45, 212, 191, 0.5)" strokeWidth="1.5" />
          {ordered.map((d, i) => {
            const a = angles[i]
            const lx = cx + labelR * Math.cos(a)
            const ly = cy - labelR * Math.sin(a)
            const isActive = activeIdx === i
            const isSelected = selectedAxis === i
            return (
              <g
                key={d.title}
                style={{ cursor: 'pointer' }}
                onMouseEnter={(e) => handleAxisEnter(i, e)}
                onMouseLeave={() => setHoverAxis(null)}
                onClick={(e) => {
                  handleAxisEnter(i, e)
                  setSelectedAxis(selectedAxis === i ? null : i)
                }}
              >
                <circle cx={lx} cy={ly} r={36} fill="transparent" />
                {isSelected && (
                  <circle cx={lx} cy={ly} r={32} fill="none" stroke="rgba(45,212,191,0.35)" strokeWidth="1" strokeDasharray="4 3" />
                )}
                <text
                  x={lx} y={ly} textAnchor="middle" dominantBaseline="middle"
                  style={{
                    fill: isActive ? 'rgb(94, 234, 212)' : 'rgba(255,255,255,0.72)',
                    fontSize: 11,
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                    letterSpacing: '0.06em',
                    filter: isActive ? 'drop-shadow(0 0 8px rgba(45,212,191,0.6))' : undefined,
                    transition: 'fill 0.2s ease, filter 0.2s ease'
                  }}
                >
                  {axisLabels[i]}
                </text>
              </g>
            )
          })}
        </svg>

        {/* Hover tooltip */}
        <div
          className="pointer-events-none absolute z-50 w-72 rounded-md border border-teal-500/30 bg-gradient-to-br from-[#0a1a1f] via-[#0d1117] to-[#0b0d10] px-4 py-3 font-mono text-xs shadow-[0_0_32px_rgba(45,212,191,0.12),0_0_2px_rgba(45,212,191,0.3)] backdrop-blur-sm"
          style={{
            left: tooltipPos.x,
            top: tooltipPos.y,
            transform: hoverAxis !== null ? 'translate(-50%, calc(-100% - 18px)) scale(1)' : 'translate(-50%, calc(-100% - 10px)) scale(0.9)',
            opacity: hoverAxis !== null ? 1 : 0,
            transition: 'opacity 0.2s ease, transform 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        >
          {hoverAxis !== null && (
            <>
              <div className="mb-2 flex items-baseline justify-between border-b border-teal-500/20 pb-1.5">
                <span className="text-[9px] uppercase tracking-[0.3em] text-teal-400/70">{'// signal decoded'}</span>
                <span className="text-[9px] tabular-nums text-teal-600/50">CH-{String(hoverAxis + 1).padStart(2, '0')}</span>
              </div>
              <p className="mb-1 text-[10px] tracking-widest text-teal-300 [text-shadow:0_0_10px_rgba(45,212,191,0.3)]">
                {AXIS_INTEL[hoverAxis].signal}
              </p>
              <p className="mb-1.5 font-sans text-[13px] font-semibold leading-snug tracking-tight text-text/95">
                {AXIS_INTEL[hoverAxis].what}
              </p>
            </>
          )}
        </div>

        <p className="mt-4 max-w-2xl text-center text-sm text-text/90">{interpretation}</p>
      </div>

      {/* Inline detail panel for selected axis */}
      {selectedAxis !== null && (
        <div className="rounded border border-teal-500/25 bg-black/30 p-4 space-y-3">
          <div className="flex items-baseline justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.28em] text-teal-400/80">
                {AXIS_INTEL[selectedAxis].signal}
              </p>
              <p className="mt-1 text-sm font-medium text-text">{AXIS_INTEL[selectedAxis].what}</p>
            </div>
            <span className={`text-sm font-semibold ${STRENGTH_COLOR[ordered[selectedAxis].strength]}`}>
              {ordered[selectedAxis].strength}
            </span>
          </div>
          <p className="text-xs text-muted">
            {viewMode === 'beginner' ? AXIS_INTEL[selectedAxis].beginner : AXIS_INTEL[selectedAxis].technical}
          </p>
          {catIssues.length > 0 ? (
            <div className="space-y-2">
              <p className="text-[10px] uppercase tracking-[0.18em] text-muted">
                triggered issues ({catIssues.length})
              </p>
              {catIssues.map((iss) => (
                <div key={iss.id} className="rounded border border-white/10 bg-black/20 p-2.5 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-text/90">{iss.title}</span>
                    <span className={`rounded-full border px-1.5 py-0.5 text-[9px] font-semibold ${iss.severity === 'HIGH' ? 'border-red-400/60 text-red-300' : iss.severity === 'MED' ? 'border-yellow-300/50 text-yellow-200' : 'border-white/20 text-muted'}`}>
                      {iss.severity}
                    </span>
                  </div>
                  <p className="mt-1 text-muted">{iss.description}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-teal-300/70">No issues triggered in this category.</p>
          )}
          <button
            type="button"
            onClick={() => setSelectedAxis(null)}
            className="text-[10px] text-muted hover:text-text/70"
          >
            Close panel
          </button>
        </div>
      )}
    </div>
  )
}
