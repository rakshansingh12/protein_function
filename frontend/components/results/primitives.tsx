'use client'

import { motion } from 'framer-motion'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { CountUp } from '@/components/motion-primitives'
import { cn } from '@/lib/utils'

export function ResultBlock({
  id,
  label,
  question,
  answer,
  children,
  className,
}: {
  id: string
  label: string
  question: string
  answer: React.ReactNode
  children: React.ReactNode
  className?: string
}) {
  return (
    <motion.section
      id={id}
      aria-labelledby={`${id}-q`}
      initial={{ opacity: 0, y: 28 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className={cn('glass scroll-mt-32 rounded-3xl p-5 sm:p-8', className)}
    >
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
      <h3 id={`${id}-q`} className="mt-2 text-balance text-2xl font-semibold tracking-tight">
        {question}
      </h3>
      <p className="mt-3 max-w-3xl text-pretty leading-relaxed text-muted-foreground">{answer}</p>
      <div className="mt-8">{children}</div>
    </motion.section>
  )
}

export function Ring({
  value,
  max = 100,
  size = 72,
  stroke = 6,
  colorClass = 'text-enzyme',
  decimals = 1,
  label,
}: {
  value: number
  max?: number
  size?: number
  stroke?: number
  colorClass?: string
  decimals?: number
  label: string
}) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const frac = Math.max(0, Math.min(1, value / max))
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="currentColor" strokeWidth={stroke} className="text-muted" />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth={stroke}
          strokeLinecap="round"
          className={colorClass}
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          whileInView={{ strokeDashoffset: c * (1 - frac) }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-sm font-semibold" aria-label={label}>
        <CountUp value={value} decimals={decimals} />
      </span>
    </div>
  )
}

export function ClassChip({ cls, className }: { cls: 'enzyme' | 'non_enzyme'; className?: string }) {
  const isEnz = cls === 'enzyme'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
        isEnz ? 'bg-enzyme/15 text-enzyme' : 'bg-non-enzyme/15 text-non-enzyme',
        className,
      )}
    >
      <span className={cn('size-1.5 rounded-full', isEnz ? 'bg-enzyme' : 'bg-non-enzyme')} aria-hidden="true" />
      {isEnz ? 'Enzyme' : 'Non-enzyme'}
    </span>
  )
}

export function ExternalLink({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={cn('underline decoration-border underline-offset-4 transition-colors hover:decoration-current', className)}
    >
      {children}
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  )
}

// Shared pager for long result lists (e.g. dozens of PDB entries), so a
// results card never grows into an endless scroll.
export function Pager({
  page,
  pageCount,
  total,
  pageSize,
  onChange,
  label,
}: {
  page: number
  pageCount: number
  total: number
  pageSize: number
  onChange: (page: number) => void
  label: string
}) {
  if (pageCount <= 1) return null
  const first = page * pageSize + 1
  const last = Math.min(total, (page + 1) * pageSize)
  const btn =
    'inline-flex size-7 items-center justify-center rounded-lg border transition-colors hover:bg-muted disabled:pointer-events-none disabled:opacity-40'
  return (
    <nav aria-label={label} className="mt-3 flex items-center justify-between gap-2 text-xs text-muted-foreground">
      <span aria-live="polite">{`${first}–${last} of ${total}`}</span>
      <div className="flex items-center gap-1.5">
        <button type="button" className={btn} onClick={() => onChange(page - 1)} disabled={page === 0} aria-label="Previous page">
          <ChevronLeft className="size-3.5" aria-hidden="true" />
        </button>
        <span className="min-w-12 text-center font-mono">{`${page + 1} / ${pageCount}`}</span>
        <button type="button" className={btn} onClick={() => onChange(page + 1)} disabled={page >= pageCount - 1} aria-label="Next page">
          <ChevronRight className="size-3.5" aria-hidden="true" />
        </button>
      </div>
    </nav>
  )
}
