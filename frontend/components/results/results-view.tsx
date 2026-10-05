'use client'

import { useEffect, useState } from 'react'
import { DatabaseBlock } from '@/components/results/database-block'
import { FingerprintBlock } from '@/components/results/fingerprint-block'
import { MotifsBlock } from '@/components/results/motifs-block'
import { NeighboursBlock } from '@/components/results/neighbours-block'
import { VerdictBlock } from '@/components/results/verdict-block'
import { WhyBlock } from '@/components/results/why-block'
import type { PredictResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

export function ResultsView({ data, sequence }: { data: PredictResponse; sequence: string }) {
  const chips = [
    { id: 'verdict', label: 'Verdict' },
    { id: 'why', label: 'Why' },
    { id: 'neighbours', label: 'Neighbours' },
    { id: 'fingerprint', label: 'Fingerprint' },
    { id: 'motifs', label: 'Motifs' },
    ...(data.dataset_match ? [{ id: 'database', label: 'Database' }] : []),
  ]
  const [active, setActive] = useState('verdict')

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActive(visible[0].target.id)
      },
      { rootMargin: '-30% 0px -60% 0px' },
    )
    chips.forEach((c) => {
      const el = document.getElementById(c.id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  return (
    <div className="mx-auto mt-16 max-w-6xl px-4 sm:px-6">
      <nav aria-label="Results sections" className="sticky top-16 z-40 -mx-4 mb-6 px-4 sm:mx-0 sm:px-0">
        <ul className="glass flex gap-1 overflow-x-auto rounded-full p-1 [scrollbar-width:none]">
          {chips.map((c) => (
            <li key={c.id} className="shrink-0">
              <a
                href={`#${c.id}`}
                aria-current={active === c.id ? 'true' : undefined}
                className={cn(
                  'block rounded-full px-3.5 py-1.5 text-sm transition-colors',
                  active === c.id ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {c.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      <div className="space-y-6">
        <VerdictBlock data={data} />
        <WhyBlock rows={data.comparison} />
        <NeighboursBlock neighbours={data.similar_proteins} prediction={data.prediction} />
        <FingerprintBlock features={data.features} />
        <MotifsBlock motifs={data.motifs} sequence={sequence} />
        {data.dataset_match ? <DatabaseBlock accession={data.dataset_match.accession} /> : null}
      </div>
    </div>
  )
}
