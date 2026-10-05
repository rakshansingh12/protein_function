'use client'

import { motion } from 'framer-motion'
import { ResultBlock } from '@/components/results/primitives'
import { PROPERTY_META } from '@/lib/constants'
import { fmt } from '@/lib/format'
import type { ComparisonRow } from '@/lib/types'
import { cn } from '@/lib/utils'

const VW = 320
const VH = 120
const BASE = 100
const TOP = 14

function gaussian(x: number, m: number, s: number) {
  return Math.exp(-0.5 * ((x - m) / s) ** 2) / s
}

function CurveCard({ row, index }: { row: ComparisonRow; index: number }) {
  const meta = PROPERTY_META[row.property] ?? { label: row.property }
  const { enzyme_mean: em, enzyme_std: es, non_enzyme_mean: nm, non_enzyme_std: ns, input } = row

  let lo = Math.min(em - 3 * es, nm - 3 * ns, input)
  let hi = Math.max(em + 3 * es, nm + 3 * ns, input)
  const pad = (hi - lo) * 0.04
  lo -= pad
  hi += pad
  if (meta.floor !== undefined) lo = Math.max(lo, meta.floor)
  if (meta.ceil !== undefined) hi = Math.min(hi, meta.ceil)

  const peak = Math.max(1 / es, 1 / ns)
  const sx = (x: number) => ((x - lo) / (hi - lo)) * VW
  const sy = (d: number) => BASE - (d / peak) * (BASE - TOP)

  const path = (m: number, s: number) => {
    const n = 80
    let d = `M 0 ${BASE}`
    for (let i = 0; i <= n; i++) {
      const x = lo + ((hi - lo) * i) / n
      d += ` L ${sx(x).toFixed(1)} ${sy(gaussian(x, m, s)).toFixed(1)}`
    }
    return `${d} L ${VW} ${BASE} Z`
  }

  const zE = Math.abs(input - em) / es
  const zN = Math.abs(input - nm) / ns
  const closer = zE <= zN ? 'enzyme' : 'non_enzyme'
  const mx = sx(input)
  const markerY = Math.min(sy(gaussian(input, em, es)), sy(gaussian(input, nm, ns)))

  return (
    <div className="rounded-2xl border bg-background/40 p-4 transition-transform duration-300 hover:-translate-y-0.5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold">{meta.label}</h4>
          <p className="font-mono text-xs text-muted-foreground">
            {`input ${fmt(input)}${meta.unit ? ` ${meta.unit}` : ''}`}
          </p>
        </div>
        <span
          className={cn(
            'rounded-full px-2.5 py-0.5 text-xs font-medium',
            closer === 'enzyme' ? 'bg-enzyme/15 text-enzyme' : 'bg-non-enzyme/15 text-non-enzyme',
          )}
        >
          {`closer to the ${closer === 'enzyme' ? 'enzyme' : 'non-enzyme'} average`}
        </span>
      </div>
      <svg viewBox={`0 0 ${VW} ${VH}`} className="mt-3 w-full overflow-visible" role="img" aria-label={`${meta.label}: input ${fmt(input)}, enzyme mean ${fmt(em)} ± ${fmt(es)}, non-enzyme mean ${fmt(nm)} ± ${fmt(ns)}`}>
        <motion.path
          d={path(nm, ns)}
          fill="var(--non-enzyme)"
          fillOpacity={0.22}
          stroke="var(--non-enzyme)"
          strokeWidth={1.5}
          initial={{ opacity: 0, scaleY: 0 }}
          whileInView={{ opacity: 1, scaleY: 1 }}
          viewport={{ once: true }}
          style={{ originY: 1 }}
          transition={{ duration: 0.6, delay: index * 0.06 }}
        />
        <motion.path
          d={path(em, es)}
          fill="var(--enzyme)"
          fillOpacity={0.22}
          stroke="var(--enzyme)"
          strokeWidth={1.5}
          initial={{ opacity: 0, scaleY: 0 }}
          whileInView={{ opacity: 1, scaleY: 1 }}
          viewport={{ once: true }}
          style={{ originY: 1 }}
          transition={{ duration: 0.6, delay: index * 0.06 + 0.08 }}
        />
        <line x1={0} x2={VW} y1={BASE} y2={BASE} stroke="currentColor" className="text-border" />
        {row.property === 'instability_index' && 40 > lo && 40 < hi ? (
          <g>
            <line x1={sx(40)} x2={sx(40)} y1={TOP - 4} y2={BASE} stroke="currentColor" strokeDasharray="2 3" className="text-muted-foreground" />
            <text x={sx(40) + 4} y={TOP + 2} className="fill-muted-foreground font-mono text-[9px]">40</text>
          </g>
        ) : null}
        <motion.g
          initial={{ y: -40, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ type: 'spring', stiffness: 160, damping: 14, delay: 0.4 + index * 0.06 }}
        >
          <line x1={mx} x2={mx} y1={markerY - 4} y2={BASE} stroke="currentColor" strokeWidth={2} className="text-foreground" />
          <circle cx={mx} cy={markerY - 6} r={5} className="fill-foreground" />
        </motion.g>
        <text x={0} y={VH - 2} className="fill-muted-foreground font-mono text-[9px]">{fmt(lo, 2)}</text>
        <text x={VW} y={VH - 2} textAnchor="end" className="fill-muted-foreground font-mono text-[9px]">{fmt(hi, 2)}</text>
      </svg>
      <dl className="mt-2 grid grid-cols-2 gap-2 font-mono text-[11px]">
        <div>
          <dt className="text-enzyme">enzyme</dt>
          <dd className="text-muted-foreground">{`${fmt(em)} ± ${fmt(es)}`}</dd>
        </div>
        <div>
          <dt className="text-non-enzyme">non-enzyme</dt>
          <dd className="text-muted-foreground">{`${fmt(nm)} ± ${fmt(ns)}`}</dd>
        </div>
      </dl>
      {row.property === 'instability_index' ? (
        <p className="mt-2 text-xs text-muted-foreground">
          {`Values under 40 are predicted stable (Guruprasad rule); this input is ${input < 40 ? 'under' : 'at or above'} 40.`}
        </p>
      ) : null}
    </div>
  )
}

export function WhyBlock({ rows }: { rows: ComparisonRow[] }) {
  const enzymeCloser = rows.filter((r) => Math.abs(r.input - r.enzyme_mean) / r.enzyme_std <= Math.abs(r.input - r.non_enzyme_mean) / r.non_enzyme_std).length

  return (
    <ResultBlock
      id="why"
      label="Why"
      question="Where does this protein sit compared with real enzymes and non-enzymes?"
      answer={`On ${enzymeCloser} of ${rows.length} headline properties, this protein is closer (in standard deviations) to the enzyme average than to the non-enzyme average.`}
    >
      <div className="mb-4 flex flex-wrap gap-4 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-2">
          <span className="size-3 rounded-sm bg-enzyme/40 ring-1 ring-enzyme" aria-hidden="true" />
          Enzymes (mean ± std)
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="size-3 rounded-sm bg-non-enzyme/40 ring-1 ring-non-enzyme" aria-hidden="true" />
          Non-enzymes (mean ± std)
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="size-2.5 rounded-full bg-foreground" aria-hidden="true" />
          This protein
        </span>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map((r, i) => (
          <CurveCard key={r.property} row={r} index={i} />
        ))}
      </div>
      <p className="mt-6 rounded-2xl border border-dashed p-4 text-sm leading-relaxed text-muted-foreground">
        {"The curves overlap heavily. A single property can't separate the classes; the model combines all 29."}
      </p>
    </ResultBlock>
  )
}
