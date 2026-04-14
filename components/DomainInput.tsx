'use client'

import { useRouter } from 'next/navigation'
import { FormEvent, useState } from 'react'

export function DomainInput() {
  const router = useRouter()
  const [value, setValue] = useState('')
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    setError(null)

    const trimmed = value.trim()
    if (!trimmed) {
      setError('Enter a domain or URL to scan.')
      return
    }

    const searchParams = new URLSearchParams({ target: trimmed })
    router.push(`/report?${searchParams.toString()}`)
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
      {error && <p className="text-[11px] text-red-400">{error}</p>}
    </form>
  )
}
