'use client'

import { motion } from 'framer-motion'
import { Info, SearchX } from 'lucide-react'
import { useRef, useState } from 'react'
import { ResultBlock } from '@/components/results/primitives'
import { fmt, pct } from '@/lib/format'
import { EXAMPLE_MOTIF_MATCH } from '@/lib/examples'
import type { MotifMatch, MotifResult } from '@/lib/types'
import { cn } from '@/lib/utils'

const LINE = 60

function isLowSpecificity(m: MotifMatch) {
  return m.class_rates != null && Math.abs(m.class_rates.ratio_enzyme_over_non_enzyme - 1) < 0.25
}

function MatchCard({ m, active, onSelect, example }: { m: MotifMatch; active?: boolean; onSelect?: () => void; example?: boolean }) {
  // class_rates is attached by the backend from models/motif_stats.json; absent if that file is missing.
  const r = m.class_rates
  return (
    <div className={cn('rounded-2xl border bg-background/40 p-4 transition-colors', active && 'border-enzyme/60')}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold">{m.name}</h4>
          <p className="mt-0.5 font-mono text-xs text-muted-foreground">
            <span className="rounded bg-enzyme/15 px-1 text-enzyme">{m.match}</span>
            {` at ${m.start}–${m.end}`}
          </p>
        </div>
        <div className="flex gap-2">
          {isLowSpecificity(m) ? (
            <span className="rounded-full border border-[var(--warning)]/50 bg-[var(--warning)]/10 px-2 py-0.5 text-xs text-[var(--warning)]">
              low specificity
            </span>
          ) : null}
          {onSelect && !example ? (
            <button type="button" onClick={onSelect} className="rounded-full border px-2 py-0.5 text-xs hover:bg-muted">
              Show in sequence
            </button>
          ) : null}
        </div>
      </div>
      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{m.explanation}</p>
      {r ? (
      <div className="mt-3 space-y-1.5">
        <p className="text-xs">{`Found in ${pct(r.enzyme_hits / r.enzyme_total)} of enzymes vs ${pct(r.non_enzyme_hits / r.non_enzyme_total)} of non-enzymes (ratio ${fmt(r.ratio_enzyme_over_non_enzyme)}).`}</p>
        {[
          { v: r.enzyme_hits / r.enzyme_total, cls: 'bg-enzyme', label: `enzymes ${r.enzyme_hits}/${r.enzyme_total}` },
          { v: r.non_enzyme_hits / r.non_enzyme_total, cls: 'bg-non-enzyme', label: `non-enzymes ${r.non_enzyme_hits}/${r.non_enzyme_total}` },
        ].map((b, i) => (
          <div key={b.label} className="flex items-center gap-2">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
              <motion.div
                className={cn('h-full rounded-full', b.cls)}
                initial={{ width: 0 }}
                whileInView={{ width: `${b.v * 100}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: i * 0.1 }}
              />
            </div>
            <span className="w-40 shrink-0 font-mono text-[10px] text-muted-foreground">{b.label}</span>
          </div>
        ))}
      </div>
      ) : null}
    </div>
  )
}

function SequenceViewer({
  sequence,
  matches,
  selected,
  containerRef,
}: {
  sequence: string
  matches: MotifMatch[]
  selected: number | null
  containerRef: React.RefObject<HTMLDivElement | null>
}) {
  const lines: string[] = []
  for (let i = 0; i < sequence.length; i += LINE) lines.push(sequence.slice(i, i + LINE))
  const hit = (pos: number) => matches.findIndex((m) => pos >= m.start && pos <= m.end)

  return (
    <div ref={containerRef} className="relative max-h-72 overflow-auto rounded-xl border bg-background/60 p-3 font-mono text-xs leading-6">
      {lines.map((line, li) => (
        <div key={li} data-line={li} className="flex whitespace-nowrap">
          <span className="w-12 shrink-0 select-none pr-3 text-right text-muted-foreground">{li * LINE + 1}</span>
          <span>
            {line.split('').map((aa, ci) => {
              const pos = li * LINE + ci + 1
              const h = hit(pos)
              return (
                <span
                  key={ci}
                  className={cn(
                    ci > 0 && ci % 10 === 0 && 'ml-2',
                    h !== -1 && 'rounded-sm bg-enzyme/20 text-enzyme',
                    h !== -1 && h === selected && 'bg-enzyme text-background',
                  )}
                >
                  {aa}
                </span>
              )
            })}
          </span>
        </div>
      ))}
    </div>
  )
}

export function MotifsBlock({ motifs, sequence }: { motifs: MotifResult; sequence: string }) {
  const [selected, setSelected] = useState<number | null>(null)
  const viewerRef = useRef<HTMLDivElement>(null)
  const len = Math.max(sequence.length, 1)
  const { matches } = motifs

  function focus(i: number) {
    setSelected(i)
    const container = viewerRef.current
    const line = container?.querySelector<HTMLElement>(`[data-line="${Math.floor((matches[i].start - 1) / LINE)}"]`)
    if (container && line) container.scrollTo({ top: line.offsetTop - container.clientHeight / 2 + line.clientHeight / 2, behavior: 'smooth' })
  }

  return (
    <ResultBlock
      id="motifs"
      label="Motifs"
      question="Does it contain known catalytic signatures?"
      answer={
        matches.length > 0
          ? `The scan found ${matches.length} simplified catalytic motif${matches.length === 1 ? '' : 's'}; a hit is a pattern match, not proof of catalytic function.`
          : `None of the ${motifs.not_found.length} simplified catalytic motifs in the scan were found in this sequence.`
      }
    >
      {matches.length > 0 ? (
        <>
          <div>
            <div className="mb-1 flex justify-between font-mono text-[10px] text-muted-foreground">
              <span>1</span>
              <span>{len}</span>
            </div>
            <div className="relative h-8 rounded-full bg-muted">
              {matches.map((m, i) => (
                <motion.button
                  key={`${m.name}-${m.start}`}
                  type="button"
                  aria-label={`${m.name} at ${m.start}–${m.end}`}
                  onClick={() => focus(i)}
                  initial={{ scaleY: 0, opacity: 0 }}
                  whileInView={{ scaleY: 1, opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: 0.2 + i * 0.08 }}
                  className={cn(
                    'absolute top-0 h-full min-w-2 rounded-full bg-enzyme/70 ring-offset-2 ring-offset-background transition hover:bg-enzyme focus-visible:ring-2 focus-visible:ring-ring',
                    selected === i && 'bg-enzyme ring-2 ring-enzyme',
                  )}
                  style={{ left: `${((m.start - 1) / len) * 100}%`, width: `${((m.end - m.start + 1) / len) * 100}%` }}
                />
              ))}
            </div>
          </div>
          <div className="mt-4">
            <SequenceViewer sequence={sequence} matches={matches} selected={selected} containerRef={viewerRef} />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {matches.map((m, i) => (
              <MatchCard key={`${m.name}-${m.start}`} m={m} active={selected === i} onSelect={() => focus(i)} />
            ))}
          </div>
        </>
      ) : (
        <div className="rounded-2xl border border-dashed p-6">
          <div className="flex items-start gap-3">
            <SearchX className="mt-0.5 size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
            <div>
              <p className="font-medium">No known motif hits in this sequence</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {"That's not evidence against catalytic function either: the scan covers only a few simplified patterns."}
              </p>
            </div>
          </div>
          <div className="mt-5">
            <p className="mb-2 text-xs uppercase tracking-wider text-muted-foreground">How a hit is shown · example from a different protein</p>
            <div className="opacity-80">
              <MatchCard m={EXAMPLE_MOTIF_MATCH} example />
            </div>
          </div>
        </div>
      )}

      {motifs.not_found.length > 0 ? (
        <div className="mt-6">
          <p className="mb-2 text-xs uppercase tracking-wider text-muted-foreground">Not found</p>
          <ul className="flex flex-wrap gap-2">
            {motifs.not_found.map((n) => (
              <li key={n} className="rounded-full border px-3 py-1 text-xs text-muted-foreground">
                {n}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <p className="mt-6 flex gap-2 text-xs leading-relaxed text-muted-foreground">
        <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
        {motifs.disclaimer}
      </p>
    </ResultBlock>
  )
}
