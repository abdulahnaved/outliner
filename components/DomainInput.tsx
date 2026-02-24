'use client'

import { useRouter } from 'next/navigation'
import { FormEvent, useState } from 'react'
import { normalizeDomain } from '../lib/normalizeDomain'

export function DomainInput() {
  const router = useRouter()
  const [value, setValue] = useState('')
  const [checked, setChecked] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    setError(null)

    const normalized = normalizeDomain(value)
    if (!normalized) {
      setError('Enter a valid domain, like example.com.')
      return
    }
    if (!checked) {
      setError('Confirm you own the domain or have permission to test it.')
      return
    }

    const searchParams = new URLSearchParams({ domain: normalized })
    router.push(`/report/demo?${searchParams.toString()}`)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          type="text"
          inputMode="url"
          autoComplete="off"
          placeholder="example.com"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="w-full rounded border border-white/15 bg-black/20 px-3 py-2 text-sm text-text placeholder:text-muted focus:border-red-500/80 focus:outline-none focus:ring-0 sm:text-base"
        />
        <button
          type="submit"
          className="h-10 rounded border border-red-500/70 bg-red-500/15 px-4 text-xs font-semibold tracking-wide text-red-500 shadow-glow transition hover:border-red-500 hover:bg-red-500/25 sm:h-auto sm:px-6"
        >
          RUN SCAN
        </button>
      </div>
      <label className="flex items-start gap-2 text-[11px] text-muted">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
          className="mt-[2px] h-3.5 w-3.5 rounded border border-white/20 bg-black/40 text-accent focus:ring-0"
        />
        <span>I own this domain or have permission to test it.</span>
      </label>
      {error && <p className="text-[11px] text-red-400">{error}</p>}
    </form>
  )
}

