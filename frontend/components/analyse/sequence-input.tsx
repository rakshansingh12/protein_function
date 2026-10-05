'use client'

import { AlertCircle, FlaskConical, RotateCcw, Sparkles } from 'lucide-react'
import { useId } from 'react'
import { Button } from '@/components/ui/button'
import { EXAMPLE_FASTA } from '@/lib/examples'
import { MAX_CHARS, MIN_RESIDUES, validateSequence } from '@/lib/sequence'
import { cn } from '@/lib/utils'

export function SequenceInput({
  value,
  onChange,
  onSubmit,
  loading,
  apiError,
}: {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  loading: boolean
  apiError: string | null
}) {
  const id = useId()
  const v = validateSequence(value)
  const touched = value.trim().length > 0

  const problems: string[] = []
  if (touched) {
    if (v.tooLong) problems.push(`Input is ${value.length.toLocaleString()} characters; the maximum is ${MAX_CHARS.toLocaleString()}.`)
    if (v.invalidChars.length > 0) problems.push('Only the 20 standard amino acids are accepted. Offending characters:')
    if (v.tooShort) problems.push(`At least ${MIN_RESIDUES} residues are needed (currently ${v.length}).`)
  }

  const counterTone = !touched ? 'text-muted-foreground' : v.ok ? 'text-enzyme' : 'text-destructive'

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (v.ok && !loading) onSubmit()
      }}
      className="glass rounded-2xl p-4 sm:p-5"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <label htmlFor={id} className="text-sm font-medium">
          Protein sequence <span className="font-normal text-muted-foreground">(raw or FASTA)</span>
        </label>
        <span className={cn('font-mono text-xs tabular-nums', counterTone)} aria-live="polite">
          {v.length.toLocaleString()} residues
        </span>
      </div>
      <textarea
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
        autoCapitalize="characters"
        autoComplete="off"
        rows={9}
        aria-invalid={touched && !v.ok}
        aria-describedby={`${id}-help`}
        placeholder={'>sp|P00918|CAH2_HUMAN Carbonic anhydrase 2\nMSHHWGYGKHNGPEHWHKDFPIAKGERQSPVDIDTHTAK…'}
        className="block w-full resize-y break-all rounded-xl border border-input bg-background/60 p-4 font-mono text-sm leading-relaxed outline-none transition-colors placeholder:text-muted-foreground/60 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/40 aria-invalid:border-destructive/60"
      />

      <div id={`${id}-help`} className="mt-3 min-h-5 space-y-1.5 text-sm">
        {problems.length > 0 ? (
          problems.map((p) => (
            <p key={p} className="flex flex-wrap items-center gap-1.5 text-destructive">
              <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
              {p}
              {p.startsWith('Only') &&
                v.invalidChars.slice(0, 12).map((c) => (
                  <kbd key={c} className="rounded border border-destructive/40 bg-destructive/10 px-1.5 font-mono text-xs">
                    {c}
                  </kbd>
                ))}
            </p>
          ))
        ) : (
          <p className="text-muted-foreground">
            {`Minimum ${MIN_RESIDUES} residues · maximum ${MAX_CHARS.toLocaleString()} characters · FASTA headers are ignored.`}
          </p>
        )}
        {apiError ? (
          <p role="alert" className="flex items-start gap-1.5 rounded-lg bg-destructive/10 p-2.5 text-destructive">
            <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            {apiError}
          </p>
        ) : null}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button type="submit" size="lg" disabled={!v.ok || loading}>
          <FlaskConical className="size-4" aria-hidden="true" />
          {loading ? 'Analysing…' : 'Analyse'}
        </Button>
        <Button type="button" size="lg" variant="outline" onClick={() => onChange(EXAMPLE_FASTA)} disabled={loading}>
          <Sparkles className="size-4" aria-hidden="true" />
          Load example
        </Button>
        <Button type="button" size="lg" variant="ghost" onClick={() => onChange('')} disabled={loading || !value}>
          <RotateCcw className="size-4" aria-hidden="true" />
          Clear
        </Button>
      </div>
    </form>
  )
}
