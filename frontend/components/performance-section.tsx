'use client'

import { motion } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import useSWR from 'swr'
import { CountUp, Reveal } from '@/components/motion-primitives'
import { SectionHeading } from '@/components/section-heading'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { CONFUSION } from '@/lib/constants'
import { fmt } from '@/lib/format'
import type { ModelInfo } from '@/lib/types'
import { cn } from '@/lib/utils'

const LO = 0.6
const HI = 0.9
const x = (v: number) => `${((v - LO) / (HI - LO)) * 100}%`
const ease = [0.22, 1, 0.36, 1] as const

function HeroMetric({ info }: { info: ModelInfo }) {
  const m = info.models[info.best_model]
  if (!m) return null
  const small = [
    { k: 'F1', v: m.f1 },
    { k: 'Accuracy', v: m.accuracy },
    { k: 'Precision', v: m.precision },
    { k: 'Recall', v: m.recall },
  ]
  return (
    <Reveal className="glass rounded-3xl p-6 sm:p-8">
      <p className="text-sm text-muted-foreground">{`${info.best_model} · homology-aware test`}</p>
      <div className="mt-2 flex flex-wrap items-baseline gap-3">
        <CountUp value={m.roc_auc} decimals={4} className="text-6xl font-semibold tracking-tight sm:text-7xl" />
        <span className="text-lg text-muted-foreground">ROC-AUC</span>
      </div>
      <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {small.map((s) => (
          <div key={s.k} className="rounded-2xl border bg-background/40 p-3">
            <dt className="text-xs text-muted-foreground">{s.k}</dt>
            <dd className="mt-1 text-xl font-semibold">
              <CountUp value={s.v} decimals={4} />
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 text-xs text-muted-foreground">
        {`Trained on ${info.training_dataset_size.toLocaleString()} proteins (${info.class_counts.enzyme.toLocaleString()} enzyme, ${info.class_counts.non_enzyme.toLocaleString()} non-enzyme).`}
      </p>
    </Reveal>
  )
}

function Dumbbell({ info }: { info: ModelInfo }) {
  const rows = Object.entries(info.models).sort((a, b) => b[1].roc_auc - a[1].roc_auc)
  const base = info.size_baseline.test_roc_auc
  const best = info.models[info.best_model]

  return (
    <Reveal className="glass rounded-3xl p-5 sm:p-8">
      <h3 className="text-balance text-lg font-semibold">
        Homology leakage: how much scores drop when similar proteins {"can't"} appear in both train and test.
      </h3>
      <div className="mt-4 flex flex-wrap gap-4 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-2">
          <span className="size-3 rounded-full border-2 border-muted-foreground" aria-hidden="true" /> Random split
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="size-3 rounded-full bg-enzyme" aria-hidden="true" /> Homology-aware split
        </span>
      </div>

      <div className="relative mt-6">
        <ul className="space-y-5">
          {rows.map(([name, m], i) => {
            const isBest = name === info.best_model
            const drop = m.random_split_roc_auc - m.roc_auc
            return (
              <li key={name} className="grid gap-2 sm:grid-cols-[11rem_1fr] sm:items-center">
                <div className="flex items-baseline justify-between gap-2 sm:block">
                  <p className={cn('text-sm', isBest && 'font-semibold')}>{name}</p>
                  <p className="font-mono text-[11px] text-muted-foreground">
                    {`${fmt(m.random_split_roc_auc)} → ${fmt(m.roc_auc)} (−${fmt(drop)})`}
                  </p>
                </div>
                <div className="relative h-6">
                  <div className="absolute inset-x-0 top-1/2 h-px bg-border" />
                  <motion.div
                    className="absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-gradient-to-r from-enzyme to-muted-foreground/60"
                    style={{ left: x(m.roc_auc) }}
                    initial={{ width: 0 }}
                    whileInView={{ width: `${(drop / (HI - LO)) * 100}%` }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.4, delay: 0.1 + i * 0.08 }}
                  />
                  <span
                    className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-muted-foreground bg-background"
                    style={{ left: x(m.random_split_roc_auc) }}
                    aria-hidden="true"
                  />
                  <motion.span
                    className={cn('absolute top-1/2 -translate-y-1/2 rounded-full bg-enzyme', isBest ? 'size-4' : 'size-3.5')}
                    style={{ marginLeft: isBest ? -8 : -7 }}
                    initial={{ left: x(m.random_split_roc_auc) }}
                    whileInView={{ left: x(m.roc_auc) }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.8, delay: 0.2 + i * 0.08, ease }}
                    aria-hidden="true"
                  />
                </div>
              </li>
            )
          })}
        </ul>

        <div className="pointer-events-none absolute inset-y-0 left-0 right-0 sm:left-[11.5rem]" aria-hidden="true">
          <div className="absolute -top-3 -bottom-2 w-px border-l border-dashed border-non-enzyme" style={{ left: x(base) }} />
        </div>
      </div>

      <div className="mt-3 sm:ml-[11.5rem]">
        <div className="relative h-4 font-mono text-[10px] text-muted-foreground">
          {[0.6, 0.7, 0.8, 0.9].map((t) => (
            <span key={t} className="absolute -translate-x-1/2 first:translate-x-0 last:-translate-x-full" style={{ left: x(t) }}>
              {t.toFixed(1)}
            </span>
          ))}
        </div>

        {best ? (
          <div className="relative mt-6 h-14">
            <motion.div
              className="absolute top-0 h-3 border-x-2 border-t-2 border-foreground/70"
              style={{ left: x(base) }}
              initial={{ width: 0 }}
              whileInView={{ width: `${((best.roc_auc - base) / (HI - LO)) * 100}%` }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 0.5, ease }}
            />
            <p className="absolute top-4 text-xs" style={{ left: x(base) }}>
              <span className="font-mono font-semibold">{`+${fmt(info.size_baseline.lift_of_full_model)}`}</span>
              <span className="text-muted-foreground">{` lift of ${info.best_model} over size alone`}</span>
            </p>
          </div>
        ) : null}
      </div>
      <p className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
        <span className="h-3 border-l border-dashed border-non-enzyme" aria-hidden="true" />
        {`Size-only baseline (MW + length): ${fmt(base)} ROC-AUC, what size alone gets you.`}
      </p>
    </Reveal>
  )
}

function ConfusionMatrix() {
  const { tn, fp, fn, tp } = CONFUSION
  const max = Math.max(tn, fp, fn, tp)
  const cells = [
    { k: 'TN', v: tn, desc: 'non-enzyme, predicted non-enzyme', color: 'var(--non-enzyme)' },
    { k: 'FP', v: fp, desc: 'non-enzyme, predicted enzyme', color: 'var(--muted-foreground)' },
    { k: 'FN', v: fn, desc: 'enzyme, predicted non-enzyme', color: 'var(--muted-foreground)' },
    { k: 'TP', v: tp, desc: 'enzyme, predicted enzyme', color: 'var(--enzyme)' },
  ]
  return (
    <Reveal className="glass rounded-3xl p-5 sm:p-8">
      <h3 className="text-lg font-semibold">Confusion matrix · Extra Trees test set</h3>
      <div className="mt-6 grid grid-cols-[auto_1fr_1fr] gap-2 text-xs">
        <span />
        <span className="text-center text-muted-foreground">Predicted non-enzyme</span>
        <span className="text-center text-muted-foreground">Predicted enzyme</span>
        {[0, 1].map((row) => (
          <div key={row} className="contents">
            <span className="flex items-center pr-1 text-muted-foreground [writing-mode:vertical-rl] rotate-180 sm:[writing-mode:horizontal-tb] sm:rotate-0">
              {row === 0 ? 'Actual non-enzyme' : 'Actual enzyme'}
            </span>
            {cells.slice(row * 2, row * 2 + 2).map((c, i) => (
              <div key={c.k} className="relative aspect-[4/3] overflow-hidden rounded-2xl border">
                <motion.div
                  className="absolute inset-0"
                  style={{ backgroundColor: c.color }}
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 0.12 + (c.v / max) * 0.5 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, delay: (row * 2 + i) * 0.1 }}
                />
                <div className="relative flex h-full flex-col justify-between p-3">
                  <span className="font-mono text-xs font-semibold">{c.k}</span>
                  <div>
                    <CountUp value={c.v} className="text-2xl font-semibold sm:text-3xl" />
                    <p className="text-[10px] leading-tight text-muted-foreground">{c.desc}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </Reveal>
  )
}

function EnsembleNote({ info }: { info: ModelInfo }) {
  return (
    <Collapsible className="glass rounded-3xl">
      <CollapsibleTrigger className="group flex w-full items-center justify-between gap-4 p-5 text-left font-semibold sm:p-6">
        Why not the ensemble?
        <ChevronDown className="size-4 shrink-0 transition-transform group-data-[panel-open]:rotate-180" aria-hidden="true" />
      </CollapsibleTrigger>
      <CollapsibleContent className="px-5 pb-5 text-sm leading-relaxed text-muted-foreground sm:px-6 sm:pb-6">
        <p>
          Model selection used cross-validation on the training data, not the test set. An ensemble was considered, but it
          did not clear the pre-set margin over the best single model, so the simpler {info.best_model} model was kept
          {info.ensemble_selected ? '' : ' (ensemble_selected: false)'}. This does not mean an ensemble is worse, only
          that it was not shown to be meaningfully better under the rule fixed in advance.
        </p>
        {info.selection_rule ? <p className="mt-2 font-mono text-xs">{info.selection_rule}</p> : null}
      </CollapsibleContent>
    </Collapsible>
  )
}

export function PerformanceSection() {
  const { data, error } = useSWR('model-info', api.modelInfo, { revalidateOnFocus: false })

  return (
    <section id="performance" aria-labelledby="perf-title" className="py-20 sm:py-28">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <SectionHeading
          id="perf-title"
          eyebrow="Model performance"
          title="How good is the model, honestly?"
          description="Good enough to be interesting, not good enough to replace homology-based annotation. Every number below comes from a homology-aware test split."
        />
        <div className="mt-12 space-y-4">
          {error ? (
            <p role="alert" className="rounded-2xl bg-destructive/10 p-4 text-sm text-destructive">
              Model information could not be loaded.
            </p>
          ) : !data ? (
            <div className="space-y-4" aria-busy="true">
              <Skeleton className="h-56 rounded-3xl" />
              <Skeleton className="h-72 rounded-3xl" />
            </div>
          ) : (
            <>
              <HeroMetric info={data} />
              <Dumbbell info={data} />
              <div className="grid gap-4 lg:grid-cols-2">
                <ConfusionMatrix />
                <div className="flex flex-col gap-4">
                  <EnsembleNote info={data} />
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  )
}
