'use client'

import { motion } from 'framer-motion'
import { CountUp } from '@/components/motion-primitives'
import { ResultBlock } from '@/components/results/primitives'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { AA_NAMES, CHEM_GROUPS, type ChemGroup } from '@/lib/constants'
import { decimalsOf, fmt, pct } from '@/lib/format'
import { cn } from '@/lib/utils'

const GROUP_BG: Record<ChemGroup, string> = {
  hydrophobic: 'bg-chem-hydrophobic',
  aromatic: 'bg-chem-aromatic',
  polar: 'bg-chem-polar',
  positive: 'bg-chem-positive',
  negative: 'bg-chem-negative',
  special: 'bg-chem-special',
}

const SS = [
  { key: 'helix_fraction', label: 'Helix', cls: 'bg-enzyme' },
  { key: 'turn_fraction', label: 'Turn', cls: 'bg-muted-foreground' },
  { key: 'sheet_fraction', label: 'Sheet', cls: 'bg-non-enzyme' },
] as const

export function FingerprintBlock({ features }: { features: Record<string, number> }) {
  const max = Math.max(...CHEM_GROUPS.flatMap((g) => g.residues.map((r) => features[`aa_${r}`] ?? 0)), 0.0001)
  const groupTotals = CHEM_GROUPS.map((g) => ({ ...g, total: g.residues.reduce((s, r) => s + (features[`aa_${r}`] ?? 0), 0) }))
  const top = [...groupTotals].sort((a, b) => b.total - a.total)[0]
  const ssSum = SS.reduce((s, x) => s + (features[x.key] ?? 0), 0) || 1
  const length = features.sequence_length ?? 0
  const mw = features.molecular_weight ?? 0

  return (
    <ResultBlock
      id="fingerprint"
      label="Fingerprint"
      question="What is this protein made of?"
      answer={`The largest chemistry group in this input protein is ${top.label.toLowerCase()} residues, at ${pct(top.total)} of the sequence.`}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border bg-background/40 p-4">
          <p className="text-xs uppercase tracking-wider text-muted-foreground">Length · input protein</p>
          <p className="mt-1 text-3xl font-semibold">
            <CountUp value={length} decimals={0} /> <span className="text-base font-normal text-muted-foreground">residues</span>
          </p>
        </div>
        <div className="rounded-2xl border bg-background/40 p-4">
          <p className="text-xs uppercase tracking-wider text-muted-foreground">Molecular weight · input protein</p>
          <p className="mt-1 text-3xl font-semibold">
            <CountUp value={mw} decimals={decimalsOf(mw)} /> <span className="text-base font-normal text-muted-foreground">Da</span>
          </p>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border bg-background/40 p-4">
        <p className="text-sm font-medium">Amino-acid composition · input protein</p>
        <div className="mt-4 overflow-x-auto pb-1">
          <div className="flex min-w-[36rem] items-start gap-3">
            {CHEM_GROUPS.map((g) => (
              <div key={g.key} className="flex flex-1 flex-col" style={{ flexGrow: g.residues.length }}>
                <div className="flex h-40 items-end gap-1">
                  {g.residues.map((r, i) => {
                    const v = features[`aa_${r}`] ?? 0
                    return (
                      <Tooltip key={r}>
                        <TooltipTrigger
                          render={<button type="button" />}
                          aria-label={`${AA_NAMES[r]} (${r}): ${fmt(v)}`}
                          className="group relative flex h-full flex-1 items-end rounded-t-md focus-visible:outline-2"
                        >
                          <motion.span
                            className={cn('block w-full rounded-t-md opacity-85 transition-opacity group-hover:opacity-100', GROUP_BG[g.key])}
                            initial={{ height: 0 }}
                            whileInView={{ height: `${(v / max) * 100}%` }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.6, delay: i * 0.04 }}
                          />
                        </TooltipTrigger>
                        <TooltipContent>{`${AA_NAMES[r]} · ${fmt(v)} (${pct(v)})`}</TooltipContent>
                      </Tooltip>
                    )
                  })}
                </div>
                <div className="mt-1 flex gap-1">
                  {g.residues.map((r) => (
                    <span key={r} className="flex-1 text-center font-mono text-xs">
                      {r}
                    </span>
                  ))}
                </div>
                <p className="mt-2 border-t pt-1.5 text-[11px] text-muted-foreground">
                  <span className={cn('mr-1.5 inline-block size-2 rounded-full', GROUP_BG[g.key])} aria-hidden="true" />
                  {`${g.label} · ${pct(groupTotals.find((t) => t.key === g.key)!.total, 1)}`}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border bg-background/40 p-4">
        <p className="text-sm font-medium">Secondary-structure propensity · input protein</p>
        <div className="mt-3 flex h-4 gap-0.5 overflow-hidden rounded-full" role="img" aria-label={SS.map((s) => `${s.label} ${fmt(features[s.key] ?? 0)}`).join(', ')}>
          {SS.map((s, i) => (
            <motion.div
              key={s.key}
              className={s.cls}
              initial={{ width: 0 }}
              whileInView={{ width: `${((features[s.key] ?? 0) / ssSum) * 100}%` }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.1 }}
            />
          ))}
        </div>
        <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-sm">
          {SS.map((s) => (
            <div key={s.key} className="flex items-center gap-2">
              <span className={cn('size-2.5 rounded-full', s.cls)} aria-hidden="true" />
              <dt>{s.label}</dt>
              <dd className="font-mono text-muted-foreground">{fmt(features[s.key] ?? 0)}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-2 text-xs text-muted-foreground">
          These are residue-propensity fractions, which can overlap, so they need not sum to 1. Segments are scaled relative to each other.
        </p>
      </div>
    </ResultBlock>
  )
}
