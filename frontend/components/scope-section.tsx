import { Check, X } from 'lucide-react'
import { Reveal } from '@/components/motion-primitives'
import { SectionHeading } from '@/components/section-heading'

const IS = [
  'A study of how far sequence-derived physicochemical features can go at separating enzymes from non-enzymes.',
  'Database-informed labelling: enzyme labels come from curated EC and GO annotations on reviewed UniProt entries.',
  'An honest evaluation: headline numbers come from a homology-aware split, with the size-only baseline shown alongside.',
  'A way to explore context: similar proteins in feature space, class comparisons, a simple motif scan and database links.',
]

const ISNT = [
  'Not a definitive annotation tool. A probability from this model is a hint, not a functional assignment.',
  'Not trained beyond human reviewed proteins. Other organisms or unreviewed entries are out of scope.',
  'Not state of the art. Homology-based tools perform better at this task (ECRECer, for example, reports ~93% accuracy).',
  'Not evidence of mechanism. A motif hit or a nearby neighbour does not prove catalytic function.',
]

export function ScopeSection() {
  return (
    <section id="scope" aria-labelledby="scope-title" className="py-20 sm:py-28">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <SectionHeading id="scope-title" eyebrow="Scope" title="What this is, and what it isn't." />
        <div className="mt-12 grid gap-4 md:grid-cols-2">
          <Reveal className="glass rounded-2xl p-6">
            <h3 className="text-lg font-semibold">What this is</h3>
            <ul className="mt-4 space-y-4">
              {IS.map((t) => (
                <li key={t} className="flex gap-3 text-sm leading-relaxed">
                  <Check className="mt-0.5 size-4 shrink-0 text-enzyme" aria-hidden="true" />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </Reveal>
          <Reveal delay={0.08} className="glass rounded-2xl p-6">
            <h3 className="text-lg font-semibold">{"What this isn't"}</h3>
            <ul className="mt-4 space-y-4">
              {ISNT.map((t) => (
                <li key={t} className="flex gap-3 text-sm leading-relaxed">
                  <X className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </Reveal>
        </div>
      </div>
    </section>
  )
}

export function SiteFooter() {
  return (
    <footer className="border-t py-12">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 text-sm text-muted-foreground sm:flex-row sm:items-start sm:justify-between sm:px-6">
        <div className="max-w-xl">
          <p className="font-semibold text-foreground">ProtClass</p>
          <p className="mt-2 leading-relaxed">
            An academic project classifying reviewed human proteins as enzyme or non-enzyme from 29 sequence-derived
            features, with an Extra Trees model evaluated on a homology-aware split. Built for learning and honest
            evaluation, not for definitive annotation.
          </p>
        </div>
        <p className="font-mono text-xs">Data: UniProt · AlphaFold DB · RCSB PDB · KEGG</p>
      </div>
    </footer>
  )
}
