'use client'

import { motion } from 'framer-motion'
import { ClassChip, ExternalLink, Ring, ResultBlock } from '@/components/results/primitives'
import { fmt, uniprotUrl } from '@/lib/format'
import type { Prediction, SimilarProtein } from '@/lib/types'

export function NeighboursBlock({ neighbours, prediction }: { neighbours: SimilarProtein[]; prediction: Prediction }) {
  const n = neighbours.length
  const enz = neighbours.filter((p) => p.class === 'enzyme').length
  const non = n - enz
  const majority = enz > non ? 'ENZYME' : non > enz ? 'NON-ENZYME' : null
  const agrees = majority === prediction

  const voteLine =
    n === 0
      ? 'No neighbours were returned for this sequence.'
      : majority === null
        ? `The ${n} nearest neighbours are split evenly, so the vote neither supports nor contradicts the model.`
        : `${majority === 'ENZYME' ? enz : non} of ${n} nearest neighbours are ${majority === 'ENZYME' ? 'enzymes' : 'non-enzymes'}, which ${agrees ? 'agrees' : 'disagrees'} with the model's ${prediction} prediction.`

  return (
    <ResultBlock id="neighbours" label="Neighbours" question="Which known proteins look most like this one?" answer={voteLine}>
      {n > 0 ? (
        <>
          <div>
            <div className="mb-2 flex justify-between font-mono text-xs">
              <span className="text-enzyme">{`${enz}/${n} enzyme`}</span>
              <span className="text-non-enzyme">{`${non}/${n} non-enzyme`}</span>
            </div>
            <div className="flex h-3 overflow-hidden rounded-full bg-muted" role="img" aria-label={`Neighbour vote: ${enz} enzyme, ${non} non-enzyme`}>
              <motion.div
                className="h-full bg-enzyme"
                initial={{ width: 0 }}
                whileInView={{ width: `${(enz / n) * 100}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.7 }}
              />
              <motion.div
                className="h-full bg-non-enzyme"
                initial={{ width: 0 }}
                whileInView={{ width: `${(non / n) * 100}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: 0.1 }}
              />
            </div>
          </div>
          <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {neighbours.map((p, i) => (
              <motion.li
                key={`${p.accession}-${i}`}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.07 }}
                className="flex items-center gap-4 rounded-2xl border bg-background/40 p-4 transition-transform duration-300 hover:-translate-y-1 lg:flex-col lg:items-start"
              >
                <Ring
                  value={p.similarity}
                  colorClass={p.class === 'enzyme' ? 'text-enzyme' : 'text-non-enzyme'}
                  label={`Similarity ${fmt(p.similarity)} out of 100`}
                />
                <div className="min-w-0 space-y-1.5">
                  <ExternalLink href={uniprotUrl(p.accession)} className="block font-mono text-sm font-semibold">
                    {p.accession}
                  </ExternalLink>
                  <ClassChip cls={p.class} />
                  <p className="font-mono text-[11px] text-muted-foreground">{`distance ${fmt(p.distance)}`}</p>
                </div>
              </motion.li>
            ))}
          </ul>
        </>
      ) : null}
      <p className="mt-6 text-xs leading-relaxed text-muted-foreground">
        Nearest neighbours in scaled physicochemical feature space, training split only. similarity = 100 / (1 + distance).
        This is not sequence homology.
      </p>
    </ResultBlock>
  )
}
