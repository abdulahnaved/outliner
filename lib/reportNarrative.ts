import type { Issue } from './rules'
import type { CategorySummaryStrength } from './rules'

export type ExecutiveSummary = {
  mainWeakness: string
  mainStrength: string
  priorityAction: string
}

type Cat = { title: string; strength: CategorySummaryStrength; triggered: Issue[] }

const strengthOrder: Record<CategorySummaryStrength, number> = {
  Weak: 0,
  Moderate: 1,
  Neutral: 2,
  Strong: 3
}

/**
 * High-signal one-line summary for demo / non-expert readers.
 */
export function deriveExecutiveSummary(categories: Cat[], issues: Issue[]): ExecutiveSummary {
  const sortedByRisk = [...categories].sort((a, b) => strengthOrder[a.strength] - strengthOrder[b.strength])
  const weakest = sortedByRisk[0]
  const strongest = [...categories].sort((a, b) => strengthOrder[b.strength] - strengthOrder[a.strength])[0]

  let mainWeakness = 'No critical structural weakness stood out in passive signals.'
  if (weakest && weakest.strength === 'Weak') {
    mainWeakness = `${weakest.title}: weakest area in this scan.`
  } else if (weakest && weakest.strength === 'Moderate') {
    mainWeakness = `${weakest.title}: most room for improvement.`
  } else if (issues.some((i) => i.severity === 'HIGH')) {
    const h = issues.find((i) => i.severity === 'HIGH')!
    mainWeakness = h.title
  } else if (issues.length > 0) {
    mainWeakness = issues[0].title
  }

  let mainStrength = 'No area clearly stands out as strong yet.'
  if (strongest && strongest.strength === 'Strong' && strongest.triggered.length === 0) {
    mainStrength = `${strongest.title} looks strong under passive checks.`
  } else if (strongest && strongest.strength === 'Strong') {
    mainStrength = `${strongest.title} still scores well relative to other categories.`
  } else if (categories.some((c) => c.strength === 'Strong')) {
    const s = categories.find((c) => c.strength === 'Strong')
    if (s) mainStrength = `${s.title} is a relative strength.`
  }

  let priorityAction = 'Harden headers and transport defaults, then iterate on content policy.'
  const hi = issues.find((i) => i.severity === 'HIGH')
  const pick = hi ?? issues[0]
  if (pick) {
    const one = pick.recommendation.trim()
    const sentence = one.split(/(?<=[.!?])\s/)[0] ?? one
    priorityAction = sentence.length > 140 ? `${sentence.slice(0, 137)}…` : sentence
  }

  return { mainWeakness, mainStrength, priorityAction }
}

export type ReliabilityTier = 'higher' | 'moderate' | 'lower'

export type MlReliability = {
  tier: ReliabilityTier
  label: string
  explanation: string
}

/**
 * Conservative frontend-only reliability estimate. Does not claim statistical confidence.
 */
export function deriveMlReliability(
  predictionAvailable: boolean,
  percentile: number | null | undefined,
  predictionError: string | null | undefined,
  features: Record<string, unknown>
): MlReliability {
  if (!predictionAvailable) {
    return {
      tier: 'lower',
      label: 'Estimate unavailable',
      explanation:
        'No learned score was produced for this scan. Use the rule baseline and raw signals below.'
    }
  }
  if (predictionError) {
    return {
      tier: 'lower',
      label: 'Lower reliability',
      explanation:
        'The model returned an error for this scan. Treat any cached or partial output as indicative only.'
    }
  }

  if (percentile == null || Number.isNaN(percentile)) {
    return {
      tier: 'moderate',
      label: 'Moderate reliability',
      explanation:
        'The estimate uses passive features only; dataset position was not available—compare with the rule baseline and raw evidence.'
    }
  }

  const keys = Object.keys(features ?? {}).length
  const sparse = keys > 0 && keys < 8

  // Score percentile as proxy for "how typical" this site's posture is vs. the logged dataset
  if (percentile >= 25 && percentile <= 75 && !sparse) {
    return {
      tier: 'higher',
      label: 'Higher reliability',
      explanation:
        'The passive signal pattern is close to many previously scanned sites; the estimate is a reasonable first read—still validate against rules and evidence.'
    }
  }

  if ((percentile >= 10 && percentile < 25) || (percentile > 75 && percentile <= 90)) {
    return {
      tier: 'moderate',
      label: 'Moderate reliability',
      explanation:
        'The site sits somewhat toward the edge of the observed score range; treat the number as indicative and read the compare view for rule–model tension.'
    }
  }

  if (percentile < 10 || percentile > 90 || sparse) {
    return {
      tier: 'lower',
      label: 'Lower reliability',
      explanation:
        'This site has a less common feature mix or an edge-of-distribution score; use the estimate as directional and weigh it against the deterministic baseline.'
    }
  }

  return {
    tier: 'moderate',
    label: 'Moderate reliability',
    explanation:
      'The model generalizes from passive signals; divergence from the rule engine highlights different sensitivities, not a single ground truth.'
  }
}

export type CompareDivergence = 'strong_agreement' | 'moderate_divergence' | 'large_divergence'

export function compareDivergence(delta: number): CompareDivergence {
  const d = Math.abs(delta)
  if (d <= 5) return 'strong_agreement'
  if (d <= 15) return 'moderate_divergence'
  return 'large_divergence'
}
