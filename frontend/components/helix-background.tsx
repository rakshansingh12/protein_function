'use client'

import { motion, useReducedMotion } from 'framer-motion'

const PERIOD = 160
const AMP = 70
const CY = 200
const WIDTH = 1600 + PERIOD

function strand(phase: number) {
  const pts: string[] = []
  for (let x = 0; x <= WIDTH; x += 8) {
    const y = CY + AMP * Math.sin((2 * Math.PI * x) / PERIOD + phase)
    pts.push(`${x === 0 ? 'M' : 'L'}${x} ${y.toFixed(1)}`)
  }
  return pts.join(' ')
}

const STRAND_A = strand(0)
const STRAND_B = strand(Math.PI)
const RUNGS = Array.from({ length: Math.floor(WIDTH / 20) }, (_, i) => {
  const x = i * 20
  const t = (2 * Math.PI * x) / PERIOD
  return { x, y1: CY + AMP * Math.sin(t), y2: CY + AMP * Math.sin(t + Math.PI), depth: Math.abs(Math.cos(t)) }
})

export function HelixBackground() {
  const reduce = useReducedMotion()

  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute left-1/2 top-1/3 size-[36rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-enzyme/15 blur-3xl" />
      <div className="absolute right-0 top-2/3 size-[28rem] translate-x-1/3 rounded-full bg-non-enzyme/15 blur-3xl" />
      <svg
        viewBox="0 0 1600 400"
        preserveAspectRatio="xMidYMid slice"
        className="absolute left-1/2 top-[55%] h-[70%] w-[160%] -translate-x-1/2 -translate-y-1/2 -rotate-12 opacity-50 dark:opacity-60"
      >
        <defs>
          <linearGradient id="helix-a" x1="0" x2="1">
            <stop offset="0" stopColor="var(--enzyme)" stopOpacity="0" />
            <stop offset="0.5" stopColor="var(--enzyme)" stopOpacity="0.9" />
            <stop offset="1" stopColor="var(--enzyme)" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="helix-b" x1="0" x2="1">
            <stop offset="0" stopColor="var(--non-enzyme)" stopOpacity="0" />
            <stop offset="0.5" stopColor="var(--non-enzyme)" stopOpacity="0.9" />
            <stop offset="1" stopColor="var(--non-enzyme)" stopOpacity="0" />
          </linearGradient>
          <filter id="helix-glow" x="-10%" y="-50%" width="120%" height="200%">
            <feGaussianBlur stdDeviation="4" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <motion.g
          filter="url(#helix-glow)"
          animate={reduce ? undefined : { x: [0, -PERIOD] }}
          transition={{ duration: 14, ease: 'linear', repeat: Infinity }}
        >
          {RUNGS.map((r) => (
            <line
              key={r.x}
              x1={r.x}
              x2={r.x}
              y1={r.y1}
              y2={r.y2}
              stroke="currentColor"
              className="text-foreground"
              strokeOpacity={0.05 + r.depth * 0.12}
              strokeWidth={1.5}
            />
          ))}
          <path d={STRAND_B} fill="none" stroke="url(#helix-b)" strokeWidth={3} strokeLinecap="round" />
          <path d={STRAND_A} fill="none" stroke="url(#helix-a)" strokeWidth={3} strokeLinecap="round" />
        </motion.g>
      </svg>
      <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-b from-transparent to-background" />
    </div>
  )
}
