'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'

/** Block open redirects: only same-origin relative paths */
function safeInternalRedirect(raw: string | null, fallback: string): string {
  if (!raw || !raw.startsWith('/') || raw.startsWith('//') || raw.includes('://')) {
    return fallback
  }
  return raw
}

function AccountForm() {
  const router = useRouter()
  const [rawSearch, setRawSearch] = useState<string>('') // avoids Suspense/hydration edge-cases
  useEffect(() => {
    setRawSearch(window.location.search ?? '')
  }, [])

  const searchParams = useMemo(() => new URLSearchParams(rawSearch), [rawSearch])
  const nextPath = safeInternalRedirect(searchParams.get('next'), '/dashboard')

  const modeFromUrl = searchParams.get('mode') === 'register' ? 'register' : 'login'
  const [mode, setMode] = useState<'login' | 'register'>('login')

  useEffect(() => {
    setMode(modeFromUrl)
  }, [modeFromUrl])

  const setSearchMode = useCallback(
    (next: 'login' | 'register') => {
      const qs = new URLSearchParams(searchParams.toString())
      if (next === 'register') {
        qs.set('mode', 'register')
      } else {
        qs.delete('mode')
      }
      const s = qs.toString()
      router.replace(s ? `/login?${s}` : '/login', { scroll: false })
      setRawSearch(s ? `?${s}` : '')
    },
    [router, searchParams]
  )

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: email.trim(), password })
      })
      const data = (await res.json().catch(() => null)) as { error?: string } | null
      if (!res.ok) {
        setError(typeof data?.error === 'string' ? data.error : 'Login failed.')
        return
      }
      router.push(nextPath)
      router.refresh()
    } catch {
      setError('Network error.')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: email.trim(), password })
      })
      const data = (await res.json().catch(() => null)) as { error?: string } | null
      if (!res.ok) {
        setError(typeof data?.error === 'string' ? data.error : 'Registration failed.')
        return
      }
      router.push(nextPath)
      router.refresh()
    } catch {
      setError('Network error.')
    } finally {
      setLoading(false)
    }
  }

  const tabClass = (active: boolean) =>
    `rounded border px-3 py-1.5 text-[11px] font-mono font-semibold tracking-wide transition ${
      active
        ? 'border-red-500/70 bg-red-500/10 text-red-400'
        : 'border-white/15 text-muted hover:border-white/30 hover:text-text'
    }`

  return (
    <div className="mx-auto max-w-md space-y-8 pt-4">
      <div>
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted">account</p>
        <h1 className="mt-2 text-xl font-semibold text-text">
          {mode === 'login' ? 'Log in' : 'Sign up'}
        </h1>
        <div className="mt-4 flex flex-wrap gap-2" role="tablist" aria-label="Account">
          <button type="button" role="tab" aria-selected={mode === 'login'} className={tabClass(mode === 'login')} onClick={() => setSearchMode('login')}>
            Log in
          </button>
          <button type="button" role="tab" aria-selected={mode === 'register'} className={tabClass(mode === 'register')} onClick={() => setSearchMode('register')}>
            Sign up
          </button>
        </div>
      </div>

      {mode === 'login' ? (
        <form onSubmit={(ev) => void handleLogin(ev)} className="space-y-4">
          <div>
            <label htmlFor="login-email" className="mb-1 block text-[11px] uppercase tracking-[0.14em] text-muted">
              Email
            </label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(ev) => setEmail(ev.target.value)}
              className="w-full rounded border border-white/15 bg-black/20 px-3 py-2 text-sm text-text focus:border-red-500/80 focus:outline-none"
              required
            />
          </div>
          <div>
            <label htmlFor="login-password" className="mb-1 block text-[11px] uppercase tracking-[0.14em] text-muted">
              Password
            </label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(ev) => setPassword(ev.target.value)}
              className="w-full rounded border border-white/15 bg-black/20 px-3 py-2 text-sm text-text focus:border-red-500/80 focus:outline-none"
              required
              minLength={8}
            />
          </div>
          {error ? <p className="text-xs text-red-400">{error}</p> : null}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded border border-red-500/70 bg-red-500/15 py-2.5 text-xs font-semibold tracking-wide text-red-500 shadow-glow transition hover:border-red-500 hover:bg-red-500/25 disabled:opacity-50"
          >
            {loading ? 'SIGNING IN…' : 'SIGN IN'}
          </button>
        </form>
      ) : (
        <form onSubmit={(ev) => void handleRegister(ev)} className="space-y-4">
          <div>
            <label htmlFor="reg-email" className="mb-1 block text-[11px] uppercase tracking-[0.14em] text-muted">
              Email
            </label>
            <input
              id="reg-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(ev) => setEmail(ev.target.value)}
              className="w-full rounded border border-white/15 bg-black/20 px-3 py-2 text-sm text-text focus:border-red-500/80 focus:outline-none"
              required
            />
          </div>
          <div>
            <label htmlFor="reg-password" className="mb-1 block text-[11px] uppercase tracking-[0.14em] text-muted">
              Password
            </label>
            <input
              id="reg-password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(ev) => setPassword(ev.target.value)}
              className="w-full rounded border border-white/15 bg-black/20 px-3 py-2 text-sm text-text focus:border-red-500/80 focus:outline-none"
              required
              minLength={8}
              maxLength={72}
            />
            <p className="mt-1 text-[11px] text-muted">8–72 characters.</p>
          </div>
          {error ? <p className="text-xs text-red-400">{error}</p> : null}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded border border-red-500/70 bg-red-500/15 py-2.5 text-xs font-semibold tracking-wide text-red-500 shadow-glow transition hover:border-red-500 hover:bg-red-500/25 disabled:opacity-50"
          >
            {loading ? 'CREATING…' : 'CREATE ACCOUNT'}
          </button>
        </form>
      )}

      <p className="text-center text-sm text-muted">
        <Link href="/" className="text-red-400/90 underline-offset-2 hover:underline">
          ← Back to home
        </Link>
      </p>
    </div>
  )
}

export default function LoginPage() {
  return <AccountForm />
}
