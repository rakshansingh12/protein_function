'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import { AlertCircle, ArrowUpRight } from 'lucide-react'
import useSWR from 'swr'
import { ExternalLink, Pager, Ring, ResultBlock } from '@/components/results/primitives'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { fmt, pct } from '@/lib/format'
import type { EnrichResponse } from '@/lib/types'

function SourceCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col rounded-2xl border bg-background/40 p-4 transition-transform duration-300 hover:-translate-y-0.5">
      <h4 className="font-mono text-xs uppercase tracking-wider text-muted-foreground">{title}</h4>
      <div className="mt-3 flex-1">{children}</div>
    </div>
  )
}

const NotAvailable = () => <p className="text-sm text-muted-foreground">Not available for this protein.</p>

function Chip({ href, children }: { href?: string; children: React.ReactNode }) {
  const cls = 'inline-flex max-w-full items-center gap-1 truncate rounded-full border px-2.5 py-1 text-xs'
  return href ? (
    <a href={href} target="_blank" rel="noopener noreferrer" className={`${cls} transition-colors hover:bg-muted`}>
      {children}
      <ArrowUpRight className="size-3 shrink-0" aria-hidden="true" />
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  ) : (
    <span className={cls}>{children}</span>
  )
}

// Well-studied proteins can have dozens of PDB entries; show them a page at a time.
const PDB_PAGE_SIZE = 6

function PdbList({ entries }: { entries: NonNullable<EnrichResponse['pdb']> }) {
  const [page, setPage] = useState(0)
  const pageCount = Math.ceil(entries.length / PDB_PAGE_SIZE)
  const shown = entries.slice(page * PDB_PAGE_SIZE, (page + 1) * PDB_PAGE_SIZE)
  return (
    <div>
      <ul className="grid gap-2 sm:grid-cols-2">
        {shown.map((e) => (
          <li key={e.id}>
            <a
              href={e.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block rounded-xl border p-3 transition-colors hover:bg-muted"
            >
              <span className="flex items-center justify-between font-mono text-sm font-semibold">
                {e.id}
                <ArrowUpRight className="size-3.5" aria-hidden="true" />
              </span>
              <span className="mt-1 block text-xs text-muted-foreground">
                {[e.method, e.resolution, e.chains].filter(Boolean).join(' · ')}
              </span>
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
          </li>
        ))}
      </ul>
      <Pager
        page={page}
        pageCount={pageCount}
        total={entries.length}
        pageSize={PDB_PAGE_SIZE}
        onChange={setPage}
        label="PDB structures pages"
      />
    </div>
  )
}

function Cards({ data }: { data: EnrichResponse }) {
  const { uniprot, alphafold, pdb, kegg } = data
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <SourceCard title="UniProt">
        {uniprot ? (
          <div className="space-y-3">
            <p className="font-semibold">{uniprot.protein_name}</p>
            <p className="text-sm text-muted-foreground">
              Organism: <span className="italic text-foreground">{uniprot.organism}</span>
            </p>
            {uniprot.subcellular_locations.length > 0 ? (
              <ul className="flex flex-wrap gap-2" aria-label="Subcellular locations">
                {uniprot.subcellular_locations.map((l) => (
                  <li key={l}>
                    <Chip>{l}</Chip>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground">No subcellular location listed.</p>
            )}
          </div>
        ) : (
          <NotAvailable />
        )}
      </SourceCard>

      <SourceCard title="AlphaFold DB">
        {alphafold ? (
          <div>
            <div className="flex items-center gap-4">
              <Ring value={alphafold.mean_plddt} size={84} decimals={2} label={`Mean pLDDT ${fmt(alphafold.mean_plddt)} out of 100`} />
              <div className="min-w-0">
                <p className="text-sm font-medium">Mean pLDDT</p>
                <ExternalLink href={alphafold.url} className="font-mono text-xs">
                  {alphafold.entry_id}
                </ExternalLink>
              </div>
            </div>
            <div className="mt-4">
              <div className="mb-1 flex justify-between text-xs">
                <span>Fraction with very low pLDDT</span>
                <span className="font-mono">{fmt(alphafold.fraction_plddt_very_low)}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <motion.div
                  className="h-full rounded-full bg-non-enzyme"
                  initial={{ width: 0 }}
                  whileInView={{ width: pct(alphafold.fraction_plddt_very_low) }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7 }}
                />
              </div>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
              We retrieve precomputed AlphaFold models; pLDDT is prediction confidence, a proxy for disorder, not disorder itself.
            </p>
          </div>
        ) : (
          <NotAvailable />
        )}
      </SourceCard>

      <SourceCard title="RCSB PDB">
        {pdb && pdb.length > 0 ? (
          <PdbList entries={pdb} />
        ) : pdb ? (
          <p className="text-sm text-muted-foreground">No experimental structures listed.</p>
        ) : (
          <NotAvailable />
        )}
      </SourceCard>

      <SourceCard title="KEGG">
        {kegg ? (
          <div className="space-y-3">
            <div>
              <p className="mb-1.5 text-xs text-muted-foreground">Pathways</p>
              {kegg.pathways.length > 0 ? (
                <ul className="flex flex-wrap gap-2">
                  {kegg.pathways.map((p) => (
                    <li key={p.id} className="max-w-full">
                      <Chip href={p.url}>{p.name}</Chip>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs">None listed.</p>
              )}
            </div>
            <div>
              <p className="mb-1.5 text-xs text-muted-foreground">EC numbers</p>
              {kegg.ec.length > 0 ? (
                <ul className="flex flex-wrap gap-2">
                  {kegg.ec.map((ec) => (
                    <li key={ec}>
                      <Chip href={`https://www.kegg.jp/entry/ec:${ec}`}>{`EC ${ec}`}</Chip>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs">None listed.</p>
              )}
            </div>
            {kegg.genes.length > 0 ? (
              <div>
                <p className="mb-1.5 text-xs text-muted-foreground">Genes</p>
                <ul className="flex flex-wrap gap-2">
                  {kegg.genes.map((g) => (
                    <li key={g.gene}>
                      <Chip href={g.url}>
                        <span className="font-mono">{g.gene}</span>
                      </Chip>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : (
          <NotAvailable />
        )}
      </SourceCard>
    </div>
  )
}

function LoadingCards() {
  return (
    <div className="grid gap-4 md:grid-cols-2" aria-busy="true" aria-label="Loading database records">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="space-y-3 rounded-2xl border bg-background/40 p-4">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
          <Skeleton className="h-16 w-full" />
        </div>
      ))}
    </div>
  )
}

export function DatabaseBlock({ accession }: { accession: string }) {
  const { data, error, isLoading } = useSWR(['enrich', accession], () => api.enrich(accession), { revalidateOnFocus: false })

  const available = data ? (['uniprot', 'alphafold', 'pdb', 'kegg'] as const).filter((k) => data[k]).length : 0

  return (
    <ResultBlock
      id="database"
      label="Database"
      question="What do curated databases already know?"
      answer={
        data
          ? `${available} of 4 external sources returned a record for ${accession}.`
          : error
            ? `External records for ${accession} could not be loaded.`
            : `Looking up ${accession} in UniProt, AlphaFold DB, RCSB PDB and KEGG.`
      }
    >
      {isLoading ? (
        <LoadingCards />
      ) : error ? (
        <p role="alert" className="flex gap-2 rounded-xl bg-destructive/10 p-3 text-sm text-destructive">
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          {error instanceof Error ? error.message : 'Could not load external records.'}
        </p>
      ) : data ? (
        <Cards data={data} />
      ) : null}
    </ResultBlock>
  )
}
