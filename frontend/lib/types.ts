export type ClassLabel = 'enzyme' | 'non_enzyme'
export type Prediction = 'ENZYME' | 'NON-ENZYME'

export interface ModelMetrics {
  roc_auc: number
  f1: number
  accuracy: number
  precision: number
  recall: number
  random_split_roc_auc: number
}

export interface ModelInfo {
  best_model: string
  split_mode: string
  selection_rule?: string
  ensemble_selected: boolean
  training_dataset_size: number
  class_counts: { enzyme: number; non_enzyme: number }
  models: Record<string, ModelMetrics>
  size_baseline: { test_roc_auc: number; lift_of_full_model: number }
}

export interface ComparisonRow {
  property: string
  input: number
  enzyme_mean: number
  enzyme_std: number
  non_enzyme_mean: number
  non_enzyme_std: number
}

export interface SimilarProtein {
  accession: string
  class: ClassLabel
  distance: number
  similarity: number
}

export interface MotifClassRates {
  enzyme_hits: number
  enzyme_total: number
  enzyme_pct: number
  non_enzyme_hits: number
  non_enzyme_total: number
  ratio_enzyme_over_non_enzyme: number
}

export interface MotifMatch {
  name: string
  start: number
  end: number
  match: string
  explanation: string
  class_rates?: MotifClassRates
}

export interface MotifResult {
  matches: MotifMatch[]
  not_found: string[]
  disclaimer: string
}

export interface DatasetMatch {
  accession: string
  protein_name: string
  label: number
  evidence_class: string
  in_training_split: boolean
}

export interface PredictResponse {
  prediction: Prediction
  probability_enzyme: number
  confidence: number
  model_name: string
  sequence_length: number
  cleaned_sequence: string
  features: Record<string, number>
  comparison: ComparisonRow[]
  similar_proteins: SimilarProtein[]
  motifs: MotifResult
  dataset_match: DatasetMatch | null
  notes: string[]
}

export interface PdbEntry {
  id: string
  method: string
  resolution: string | null
  chains: string | null
  url: string
}

export interface EnrichResponse {
  uniprot: {
    protein_name: string
    organism: string
    subcellular_locations: string[]
  } | null
  pdb: PdbEntry[] | null
  alphafold: {
    entry_id: string
    mean_plddt: number
    fraction_plddt_very_low: number
    url: string
  } | null
  kegg: {
    genes: { gene: string; url: string }[]
    ec: string[]
    pathways: { id: string; name: string; url: string }[]
  } | null
}
