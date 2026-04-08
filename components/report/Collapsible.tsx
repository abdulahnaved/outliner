'use client'

import { useState } from 'react'

type Props = {
  title: string
  subtitle?: string
  defaultOpen?: boolean
  id?: string
  highlight?: boolean
  children: React.ReactNode
}

export function Collapsible({ title, subtitle, defaultOpen = true, id, highlight, children }: Props) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <section
      id={id}
      className={`rounded border bg-black/20 transition-colors duration-300 ${highlight ? 'border-teal-500/50 shadow-[0_0_12px_rgba(45,212,191,0.08)]' : 'border-white/15'}`}
    >
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-3 p-4 text-left"
      >
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted">{title}</p>
          {subtitle && <p className="mt-0.5 text-[11px] text-muted/70">{subtitle}</p>}
        </div>
        <span className={`text-muted transition-transform duration-200 ${open ? 'rotate-180' : ''}`}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M2.5 4.5L6 8L9.5 4.5" />
          </svg>
        </span>
      </button>
      <div
        className="overflow-hidden transition-[max-height,opacity] duration-300 ease-in-out"
        style={{
          maxHeight: open ? '4000px' : '0',
          opacity: open ? 1 : 0,
        }}
      >
        <div className="px-4 pb-4">{children}</div>
      </div>
    </section>
  )
}
