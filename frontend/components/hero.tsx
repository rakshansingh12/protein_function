'use client'

import { motion } from 'framer-motion'
import { ArrowDown } from 'lucide-react'
import { HelixBackground } from '@/components/helix-background'
import { CountUp } from '@/components/motion-primitives'
import { Button } from '@/components/ui/button'

const STATS = [
  { value: 10782, decimals: 0, label: 'proteins', sub: 'reviewed human, balanced classes' },
  { value: 29, decimals: 0, label: 'sequence features', sub: 'composition + physicochemistry' },
  { value: 8022, decimals: 0, label: 'homology clusters', sub: 'related proteins never split across train and test' },
]

export function Hero() {
  return (
    <section id="top" className="relative isolate overflow-hidden pt-28 pb-20 sm:pt-36 sm:pb-28">
      <HelixBackground />
      <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.05, ease: [0.22, 1, 0.36, 1] }}
          className="max-w-3xl text-balance text-5xl font-semibold leading-[1.02] tracking-tight sm:text-7xl"
        >
          Is this protein an <span className="text-enzyme">enzyme</span>?
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
          className="mt-6 max-w-2xl text-pretty text-lg leading-relaxed text-muted-foreground"
        >
          Physicochemical machine learning trained on 10,782 reviewed human proteins, evaluated honestly with a
          homology-aware split.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.25, ease: [0.22, 1, 0.36, 1] }}
          className="mt-8 flex flex-wrap gap-3"
        >
          <Button size="lg" render={<a href="#analyse" />} nativeButton={false}>
            Analyse a sequence
            <ArrowDown className="size-4" />
          </Button>
          <Button size="lg" variant="outline" className="glass" render={<a href="#how-it-works" />} nativeButton={false}>
            How it works
          </Button>
        </motion.div>

        <dl className="mt-16 grid gap-3 sm:grid-cols-3">
          {STATS.map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.35 + i * 0.08 }}
              className="glass rounded-2xl p-5"
            >
              <dt className="sr-only">{s.label}</dt>
              <dd>
                <CountUp value={s.value} decimals={s.decimals} className="text-4xl font-semibold tracking-tight" />
                <p className="mt-1 text-sm font-medium">{s.label}</p>
                <p className="text-xs text-muted-foreground">{s.sub}</p>
              </dd>
            </motion.div>
          ))}
        </dl>
      </div>
    </section>
  )
}
