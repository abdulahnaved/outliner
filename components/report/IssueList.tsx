'use client'

import { IssueCard } from '../IssueCard'
import type { Issue } from '../../lib/rules'

type Props = {
  issues: Issue[]
}

export function IssueList({ issues }: Props) {
  if (!issues || issues.length === 0) return null

  return (
    <section className="space-y-4">
      <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">recommendations</h2>
      <div className="space-y-3">
        {issues.map((issue) => (
          <IssueCard
            key={issue.id}
            title={issue.title}
            severity={issue.severity}
            category={issue.category.replaceAll('_', ' ')}
            evidence={issue.description}
            fix={issue.recommendation}
          />
        ))}
      </div>
    </section>
  )
}

