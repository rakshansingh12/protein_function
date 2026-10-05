'use client'

import { motion } from 'framer-motion'
import { AlertTriangle, Info } from 'lucide-react'
import { CountUp } from '@/components/motion-primitives'
import { ExternalLink, ResultBlock } from '@/components/results/primitives'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { CONFUSION, EVIDENCE_EXPLAINER } from '@/lib/constants'
import { fmt, pct, uniprotUrl } from '@/lib/format'
import type { PredictResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

const W = 280
const CX = W / 2
const CY = 150
const R = 120

function polar(frac: number, r = R) {
  const a = Math.PI * (1 - frac)
  return { x: CX + r * Math.cos(a), y: CY - r * Math.sin(a) }
}

function arc(from: number, to: number, r = R) {
  const s = polar(from, r)
  const e = polar(to, r)
  return `M ${s.x} ${s.y} A ${r} ${r} 0 0 1 ${e.x} ${e.y}`
}

function Gauge({ p, isEnzyme }: { p: number; isEnzyme: boolean }) {
  const t = polar(0.5, R + 14)
  const t2 = polar(0.5, R - 16)
  return (
    <svg viewBox={`0 0 ${W} 175`} className="w-full max-w-sm" role="img" aria-label={`Probability of enzyme: ${fmt(p)}`}>
      <path d={arc(0, 0.5)} fill="none" stroke="var(--non-enzyme)" strokeOpacity={0.25} strokeWidth={18} strokeLinecap="round" />
      <path d={arc(0.5, 1)} fill="none" stroke="var(--enzyme)" strokeOpacity={0.25} strokeWidth={18} strokeLinecap="round" />
      <motion.path
        d={arc(0, Math.max(p, 0.0001))}
        fill="none"
        stroke={isEnzyme ? 'var(--enzyme)' : 'var(--non-enzyme)'}
        strokeWidth={18}
        strokeLinecap="round"
        initial={{ pathLength: 0 }}
        whileInView={{ pathLength: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      />
      <line x1={t.x} y1={t.y} x2={t2.x} y2={t2.y} stroke="currentColor" strokeWidth={2} strokeDasharray="3 3" className="text-foreground" />
      <text x={t.x} y={t.y - 6} textAnchor="middle" className="fill-muted-foreground font-mono text-[10px]">
        0.5 threshold
      </text>
      <motion.g
        style={{ originX: 0.5, originY: 1 }}
        initial={{ rotate: -90 }}
        whileInView={{ rotate: -90 + 180 * p }}
        viewport={{ once: true }}
        transition={{ type: 'spring', stiffness: 60, damping: 12, delay: 0.1 }}
      >
        <line x1={CX} y1={CY} x2={CX} y2={CY - R + 22} stroke="currentColor" strokeWidth={3} strokeLinecap="round" className="text-foreground" />
      </motion.g>
      <circle cx={CX} cy={CY} r={7} className="fill-foreground" />
      <text x={CX - R} y={CY + 22} textAnchor="middle" className="fill-muted-foreground font-mono text-[11px]">0</text>
      <text x={CX + R} y={CY + 22} textAnchor="middle" className="fill-muted-foreground font-mono text-[11px]">1</text>
    </svg>
  )
}

export function VerdictBlock({ data }: { data: PredictResponse }) {
  const isEnzyme = data.prediction === 'ENZYME'
  const p = data.probability_enzyme
  const { tp, fp, tn, fn } = CONFUSION
  const trust = isEnzyme ? tp / (tp + fp) : tn / (tn + fn)
  const trustCounts = isEnzyme ? `${tp} of ${tp + fp}` : `${tn} of ${tn + fn}`
  const match = data.dataset_match

  return (
    <ResultBlock
      id="verdict"
      label="Verdict"
      question="What does the model think, and how sure is it?"
      answer={`${data.model_name} gives this ${data.sequence_length}-residue sequence a probability of ${p.toFixed(4)} of being an enzyme, which is ${p >= 0.5 ? 'above' : 'below'} the 0.5 decision threshold.`}
    >
      <div className="grid items-center gap-8 md:grid-cols-2">
        <div className="flex flex-col items-center">
          <Gauge p={p} isEnzyme={isEnzyme} />
          <p className="-mt-2 font-mono text-xs text-muted-foreground">probability_enzyme</p>
          <CountUp value={p} decimals={4} className="text-4xl font-semibold" />
        </div>
        <div>
          <motion.p
            initial={{ opacity: 0, scale: 0.92 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className={cn('text-5xl font-semibold tracking-tight sm:text-6xl', isEnzyme ? 'text-enzyme' : 'text-non-enzyme')}
          >
            {data.prediction}
          </motion.p>
          <p className="mt-2 text-sm text-muted-foreground">
            {`Model confidence ${data.confidence.toFixed(4)} · ${data.model_name}`}
          </p>
          <div className="mt-6 rounded-2xl border bg-background/40 p-4">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">How much to trust this</p>
            <p className="mt-2 text-sm leading-relaxed">
              {`In testing, when the model said ${data.prediction} it was right `}
              <strong className={isEnzyme ? 'text-enzyme' : 'text-non-enzyme'}>{pct(trust)}</strong>
              {` of the time (${trustCounts}).`}
            </p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
              <motion.div
                className={cn('h-full rounded-full', isEnzyme ? 'bg-enzyme' : 'bg-non-enzyme')}
                initial={{ width: 0 }}
                whileInView={{ width: `${trust * 100}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: 0.2 }}
              />
            </div>
            <p className="mt-2 text-xs text-muted-foreground">From the Extra Trees homology-aware test confusion matrix.</p>
          </div>
        </div>
      </div>

      {match ? (
        <div className="mt-8 space-y-3">
          <div className="rounded-2xl border bg-background/40 p-4">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Found in the dataset</p>
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm">
              <span className="font-semibold">{match.protein_name}</span>
              <ExternalLink href={uniprotUrl(match.accession)} className="font-mono">
                {match.accession}
              </ExternalLink>
              <span
                className={cn(
                  'rounded-full px-2.5 py-0.5 text-xs font-medium',
                  match.label === 1 ? 'bg-enzyme/15 text-enzyme' : 'bg-non-enzyme/15 text-non-enzyme',
                )}
              >
                {`True label: ${match.label === 1 ? 'enzyme' : 'non-enzyme'}`}
              </span>
              <Tooltip>
                <TooltipTrigger
                  render={<button type="button" />}
                  className="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-mono text-xs"
                >
                  {match.evidence_class}
                  <Info className="size-3" aria-hidden="true" />
                </TooltipTrigger>
                <TooltipContent>{EVIDENCE_EXPLAINER[match.evidence_class] ?? 'Evidence class from the labelling pipeline.'}</TooltipContent>
              </Tooltip>
            </div>
          </div>
          {match.in_training_split ? (
            <div role="note" className="flex gap-3 rounded-2xl border border-[var(--warning)]/40 bg-[var(--warning)]/10 p-4 text-sm">
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--warning)]" aria-hidden="true" />
              <p>
                <strong>Not an independent test.</strong>
                {" This protein was in the model's training split, so a correct prediction here says little about how the model generalises."}
              </p>
            </div>
          ) : null}
        </div>
      ) : null}

      {data.notes.length > 0 ? (
        <ul className="mt-6 space-y-2">
          {data.notes.map((n) => (
            <li key={n} className="flex gap-2 text-xs text-muted-foreground">
              <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
              {n}
            </li>
          ))}
        </ul>
      ) : null}
    </ResultBlock>
  )
}
