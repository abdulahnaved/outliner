import {
  buildCategorySummaries,
  evaluateRules,
  type CategorySummary,
  type CategorySummaryStrength,
  type Issue
} from '@/lib/rules'

const strengthRank: Record<CategorySummaryStrength, number> = {
  Weak: 0,
  Moderate: 1,
  Neutral: 2,
  Strong: 3
}

export function extractRuleScore(scan: Record<string, unknown>): number | null {
  for (const key of ['rule_score', 'rule_score_v2', 'rule_score_v3'] as const) {
    const v = scan[key]
    if (typeof v === 'number' && Number.isFinite(v)) return v
  }
  return null
}

export function extractMlScore(scan: Record<string, unknown>): number | null {
  if (!scan.prediction_available) return null
  const p = scan.predicted_rule_score
  if (typeof p === 'number' && Number.isFinite(p)) return p
  return null
}

export type ScanDigest = {
  issues: Issue[]
  categories: CategorySummary[]
  issueCount: number
}

export function digestScanPayload(features: Record<string, unknown>): ScanDigest {
  const issues = evaluateRules(features)
  const categories = buildCategorySummaries(issues, features)
  return { issues, categories, issueCount: issues.length }
}

export type CompareVerdict = {
  ruleWinner: 'a' | 'b' | 'tie'
  mlWinner: 'a' | 'b' | 'tie' | 'na'
  moreFindingsWorse: 'a' | 'b' | 'tie'
  strongerOverall: 'a' | 'b' | 'tie'
  biggestCategoryTitle: string
  biggestCategoryGap: number
}

/**
 * Derive a compact verdict for the summary strip. "Stronger" = higher rule score;
 * fewer passive findings breaks ties. ML tie-break is optional when both present.
 */
export function buildCompareVerdict(
  ruleA: number | null,
  ruleB: number | null,
  mlA: number | null,
  mlB: number | null,
  issueCountA: number,
  issueCountB: number,
  catA: CategorySummary[],
  catB: CategorySummary[]
): CompareVerdict {
  let ruleWinner: CompareVerdict['ruleWinner'] = 'tie'
  if (ruleA != null && ruleB != null) {
    if (ruleA > ruleB) ruleWinner = 'a'
    else if (ruleB > ruleA) ruleWinner = 'b'
  } else if (ruleA != null && ruleB == null) ruleWinner = 'a'
  else if (ruleB != null && ruleA == null) ruleWinner = 'b'

  let mlWinner: CompareVerdict['mlWinner'] = 'na'
  if (mlA != null || mlB != null) {
    if (mlA != null && mlB != null) {
      if (mlA > mlB) mlWinner = 'a'
      else if (mlB > mlA) mlWinner = 'b'
      else mlWinner = 'tie'
    } else if (mlA != null) mlWinner = 'a'
    else if (mlB != null) mlWinner = 'b'
    else mlWinner = 'na'
  }

  let moreFindingsWorse: CompareVerdict['moreFindingsWorse'] = 'tie'
  if (issueCountA > issueCountB) moreFindingsWorse = 'a'
  else if (issueCountB > issueCountA) moreFindingsWorse = 'b'

  let strongerOverall: CompareVerdict['strongerOverall'] = 'tie'
  if (ruleWinner !== 'tie') {
    strongerOverall = ruleWinner
  } else {
    if (issueCountA < issueCountB) strongerOverall = 'a'
    else if (issueCountB < issueCountA) strongerOverall = 'b'
    else if (mlWinner === 'a') strongerOverall = 'a'
    else if (mlWinner === 'b') strongerOverall = 'b'
  }

  let biggestCategoryTitle = '—'
  let biggestCategoryGap = 0
  const byCat = new Map<string, CategorySummary>()
  for (const c of catA) byCat.set(c.category, c)
  let bestTitle = ''
  let bestGap = -1
  for (const cb of catB) {
    const ca = byCat.get(cb.category)
    if (!ca) continue
    const gap = Math.abs(strengthRank[ca.strength] - strengthRank[cb.strength])
    if (gap > bestGap) {
      bestGap = gap
      bestTitle = ca.title
    }
  }
  if (bestGap > 0) {
    biggestCategoryTitle = bestTitle
    biggestCategoryGap = bestGap
  }

  return {
    ruleWinner,
    mlWinner,
    moreFindingsWorse,
    strongerOverall,
    biggestCategoryTitle,
    biggestCategoryGap
  }
}
