'use client'

import { motion, useScroll, useSpring } from 'framer-motion'
import { ClipboardPaste, Cpu, FlaskConical, Network } from 'lucide-react'
import { useRef } from 'react'
import { Reveal } from '@/components/motion-primitives'
import { SectionHeading } from '@/components/section-heading'

const STEPS = [
  {
    icon: ClipboardPaste,
    title: 'Paste a sequence',
    body: 'Raw residues or FASTA. Headers and whitespace are stripped; only the 20 standard amino acids are accepted.',
  },
  {
    icon: FlaskConical,
    title: 'Compute 29 features',
    body: '20 amino-acid fractions, length, molecular weight, aromaticity, instability index, isoelectric point, GRAVY, and helix / turn / sheet fractions.',
  },
  {
    icon: Cpu,
    title: 'Extra Trees predicts',
    body: 'A tree ensemble returns a probability of being an enzyme. The decision threshold is 0.5.',
  },
  {
    icon: Network,
    title: 'Context, not just a label',
    body: 'Similar proteins in feature space, class comparison, a simple motif scan, and links to curated databases.',
  },
]

export function HowItWorks() {
  const ref = useRef<HTMLOListElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start 80%', 'end 60%'] })
  const scaleY = useSpring(scrollYProgress, { stiffness: 120, damping: 30 })

  return (
    <section id="how-it-works" aria-labelledby="how-title" className="py-20 sm:py-28">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <SectionHeading
          id="how-title"
          eyebrow="How it works"
          title="From residues to a probability, in four steps."
          description="No alignment, no homology search. Just what can be computed from the sequence itself, which is also why the model has limits."
        />
        <ol ref={ref} className="relative mt-14 space-y-6">
          <div aria-hidden="true" className="absolute left-5 top-2 bottom-2 w-px bg-border" />
          <motion.div
            aria-hidden="true"
            style={{ scaleY }}
            className="absolute left-5 top-2 bottom-2 w-px origin-top bg-gradient-to-b from-enzyme to-non-enzyme"
          />
          {STEPS.map((s, i) => (
            <Reveal as="li" key={s.title} delay={i * 0.06} className="relative flex gap-5">
              <div className="glass relative z-10 flex size-10 shrink-0 items-center justify-center rounded-full">
                <s.icon className="size-4" aria-hidden="true" />
              </div>
              <div className="glass flex-1 rounded-2xl p-5 transition-transform duration-300 hover:-translate-y-0.5">
                <p className="font-mono text-xs text-muted-foreground">Step {i + 1}</p>
                <h3 className="mt-1 text-lg font-semibold">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.body}</p>
              </div>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  )
}
