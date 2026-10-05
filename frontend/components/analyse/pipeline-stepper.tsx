'use client'

import { AnimatePresence, motion } from 'framer-motion'
import { Check } from 'lucide-react'
import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

const STEPS = ['Cleaning sequence', 'Computing features', 'Running model', 'Finding neighbours', 'Scanning motifs']

export function PipelineStepper() {
  const [active, setActive] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setActive((a) => Math.min(a + 1, STEPS.length - 1)), 480)
    return () => clearInterval(id)
  }, [])

  return (
    <div role="status" aria-live="polite" className="glass rounded-2xl p-5">
      <p className="sr-only">{`${STEPS[active]}…`}</p>
      <ol className="grid gap-3 sm:grid-cols-5">
        {STEPS.map((step, i) => {
          const done = i < active
          const current = i === active
          return (
            <li key={step} className="flex items-center gap-3 sm:flex-col sm:items-start">
              <div
                className={cn(
                  'relative flex size-7 shrink-0 items-center justify-center rounded-full border text-xs font-mono transition-colors duration-300',
                  done && 'border-enzyme bg-enzyme text-background',
                  current && 'border-enzyme text-enzyme',
                  !done && !current && 'text-muted-foreground',
                )}
              >
                <AnimatePresence mode="wait" initial={false}>
                  {done ? (
                    <motion.span key="c" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ duration: 0.25 }}>
                      <Check className="size-3.5" aria-hidden="true" />
                    </motion.span>
                  ) : (
                    <motion.span key="n" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                      {i + 1}
                    </motion.span>
                  )}
                </AnimatePresence>
                {current ? (
                  <motion.span
                    aria-hidden="true"
                    className="absolute inset-0 rounded-full border border-enzyme"
                    animate={{ scale: [1, 1.5], opacity: [0.6, 0] }}
                    transition={{ duration: 1, repeat: Infinity }}
                  />
                ) : null}
              </div>
              <span className={cn('text-sm transition-colors', done || current ? 'text-foreground' : 'text-muted-foreground')}>
                {step}
              </span>
            </li>
          )
        })}
      </ol>
      <div className="mt-4 h-1 overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-enzyme to-non-enzyme"
          initial={{ width: '4%' }}
          animate={{ width: `${((active + 1) / STEPS.length) * 92}%` }}
          transition={{ duration: 0.4 }}
        />
      </div>
    </div>
  )
}
