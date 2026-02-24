import Link from 'next/link'

const NAV_HEIGHT = 72

export const navHeight = NAV_HEIGHT

const sections = [
  { href: '/about', label: 'ABOUT' },
  { href: '/#method', label: 'METHOD' },
  { href: '/#contact', label: 'CONTACT' }
]

export function Navbar() {
  return (
    <header
      className="fixed inset-x-0 top-0 z-40 border-b border-white/10 bg-bg/80 backdrop-blur"
      style={{ height: NAV_HEIGHT }}
    >
      <div className="mx-auto flex h-full max-w-5xl items-center px-4">
        <div className="flex flex-1">
          <Link
            href="/#scan"
            className="flex items-baseline gap-1 font-mono text-sm tracking-tight"
          >
            <span className="font-semibold text-red-500">outliner</span>
            <span className="text-white">.</span>
          </Link>
        </div>
        <nav className="flex items-center justify-center gap-6 text-xs font-mono text-muted">
          <div className="hidden gap-5 sm:flex">
            {sections.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="transition-colors hover:text-white"
              >
                {item.label}
              </Link>
            ))}
          </div>
        </nav>
        <div className="flex flex-1 justify-end">
          <Link
            href="/#scan"
            className="rounded border border-red-500/70 bg-red-500/15 px-3 py-1.5 text-[11px] font-semibold tracking-wide text-red-500 shadow-glow transition hover:border-red-500 hover:bg-red-500/25"
          >
            RUN SCAN
          </Link>
        </div>
      </div>
    </header>
  )
}

