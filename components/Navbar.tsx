'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'

const NAV_HEIGHT = 72

export const navHeight = NAV_HEIGHT

const sections = [
  { href: '/about', label: 'ABOUT' },
  { href: '/method', label: 'METHOD' },
  { href: '/#story', label: 'STORY' }
]

type MeUser = { id: number; email: string }

export function Navbar() {
  const router = useRouter()
  const pathname = usePathname()
  const [user, setUser] = useState<MeUser | null | undefined>(undefined)

  const refresh = useCallback(() => {
    fetch('/api/auth/me', { credentials: 'include', cache: 'no-store' })
      .then((r) => r.json())
      .then((j: { user?: { id?: number; email?: string } }) => {
        if (j?.user && typeof j.user.id === 'number' && typeof j.user.email === 'string') {
          setUser({ id: j.user.id, email: j.user.email })
        } else {
          setUser(null)
        }
      })
      .catch(() => setUser(null))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    // Keep nav auth state in sync after client-side login/logout navigations.
    refresh()
  }, [pathname, refresh])

  useEffect(() => {
    const onFocus = () => refresh()
    const onVis = () => {
      if (document.visibilityState === 'visible') refresh()
    }
    window.addEventListener('focus', onFocus)
    document.addEventListener('visibilitychange', onVis)
    return () => {
      window.removeEventListener('focus', onFocus)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [refresh])

  const logout = useCallback(async () => {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
    setUser(null)
    router.push('/')
    router.refresh()
  }, [router])

  const linkClass = 'text-xs font-mono transition-colors hover:text-white'
  const mutedLink = `${linkClass} text-muted`

  return (
    <header
      className="fixed inset-x-0 top-0 z-40 border-b border-white/10 bg-bg/80 backdrop-blur"
      style={{ height: NAV_HEIGHT }}
    >
      <div className="mx-auto flex h-full max-w-5xl items-center px-4">
        <div className="flex min-w-0 flex-1 justify-start">
          <Link href="/" className="flex items-baseline gap-1 font-mono text-sm tracking-tight">
            <span className="font-semibold text-red-500">outliner</span>
          </Link>
        </div>

        <nav className="flex min-w-0 flex-1 items-center justify-center gap-6 font-mono text-muted">
          <div className="hidden flex-wrap items-center justify-center gap-x-4 gap-y-2 sm:flex sm:gap-x-5">
            {sections.map((item) => (
              <Link key={item.href} href={item.href} className={`${linkClass} text-muted`}>
                {item.label}
              </Link>
            ))}
            {user ? (
              <Link href="/dashboard" className={mutedLink}>
                DASHBOARD
              </Link>
            ) : null}
          </div>
        </nav>

        <div className="flex min-w-0 flex-1 items-center justify-end">
          {user === undefined ? (
            <div
              className="h-9 w-[min(100%,200px)] max-w-full animate-pulse rounded border border-white/10 bg-white/5"
              aria-hidden
            />
          ) : user ? (
            <div className="flex items-center gap-3">
              <Link href="/dashboard" className="text-[11px] font-mono text-muted transition-colors hover:text-white sm:hidden">
                DASHBOARD
              </Link>
              <button
                type="button"
                onClick={() => void logout()}
                className="rounded border border-white/25 px-2.5 py-1.5 text-[11px] font-mono text-muted transition-colors hover:border-white/40 hover:text-white"
              >
                LOG OUT
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="rounded border border-white/20 px-2.5 py-1.5 text-[11px] font-mono text-muted transition-colors hover:border-white/40 hover:text-white"
            >
              SIGN IN
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}
