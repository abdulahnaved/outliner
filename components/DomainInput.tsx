'use client'

import { useRouter } from 'next/navigation'
import { FormEvent, useState } from 'react'

export function DomainInput() {
  const router = useRouter()
  const [value, setValue] = useState('')
  const [checked, setChecked] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)

    const trimmed = value.trim()
    if (!trimmed) {
      setError('Enter a domain or URL to scan.')
      return
    }
    if (!checked) {
      setError('Confirm you own the domain or have permission to test it.')
      return
    }

    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/api/scan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ target: trimmed })
      })

      const data = await res.json().catch(() => null)

      if (!res.ok) {
        const detail =
          (data && typeof data.detail === 'string' && data.detail) ||
          'Scan failed.'
        setError(detail)
        return
      }

      if (data) {
        if (typeof window !== 'undefined') {
          try {
            window.localStorage.setItem('outliner:lastScan', JSON.stringify(data))
          } catch {
            // ignore storage errors
          }
        }

        const searchParams = new URLSearchParams({ target: trimmed })
        router.push(`/report?${searchParams.toString()}`)
      }
    } catch {
      setError('Could not reach scanner backend.')
    } finally {
      setLoading(false)
    }
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
          disabled={loading}
          className="h-10 rounded border border-red-500/70 bg-red-500/15 px-4 text-xs font-semibold tracking-wide text-red-500 shadow-glow transition hover:border-red-500 hover:bg-red-500/25 disabled:cursor-not-allowed disabled:border-red-500/40 disabled:bg-red-500/10 sm:h-auto sm:px-6"
        >
          {loading ? 'FETCHING…' : 'RUN SCAN'}
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

