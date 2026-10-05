'use client'

import { AnimatePresence, motion } from 'framer-motion'
import { useRef, useState } from 'react'
import { PipelineStepper } from '@/components/analyse/pipeline-stepper'
import { SequenceInput } from '@/components/analyse/sequence-input'
import { ResultsView } from '@/components/results/results-view'
import { SectionHeading } from '@/components/section-heading'
import { api, ApiError } from '@/lib/api'
import type { PredictResponse } from '@/lib/types'

export function AnalyseSection() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ data: PredictResponse; sequence: string } | null>(null)
  const resultsRef = useRef<HTMLDivElement>(null)

  async function analyse() {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await api.predict(input)
      // Use the backend's cleaned sequence so motif positions match exactly what the model saw.
      setResult({ data, sequence: data.cleaned_sequence })
      requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Something went wrong while analysing this sequence.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section id="analyse" aria-labelledby="analyse-title" className="py-20 sm:py-28">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <SectionHeading
          id="analyse-title"
          eyebrow="Analyse"
          title="Paste a human protein sequence."
          description="You get a probability, not a verdict carved in stone, plus the context needed to judge it."
        />
        <div className="mt-10 space-y-4">
          <SequenceInput
            value={input}
            onChange={(v) => {
              setInput(v)
              if (error) setError(null)
            }}
            onSubmit={analyse}
            loading={loading}
            apiError={error}
          />
          <AnimatePresence>
            {loading ? (
              <motion.div
                key="stepper"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3 }}
              >
                <PipelineStepper />
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>
      </div>
      <div ref={resultsRef} data-scroll-target>
        {result ? <ResultsView data={result.data} sequence={result.sequence} /> : null}
      </div>
    </section>
  )
}
