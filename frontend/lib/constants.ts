export const CONFUSION = { tn: 764, fp: 270, fn: 242, tp: 814 } as const

export const PROPERTY_META: Record<string, { label: string; unit?: string; floor?: number; ceil?: number }> = {
  isoelectric_point: { label: 'Isoelectric point (pI)', floor: 0, ceil: 14 },
  gravy: { label: 'GRAVY (hydropathy)' },
  molecular_weight: { label: 'Molecular weight', unit: 'Da', floor: 0 },
  aromaticity: { label: 'Aromaticity', floor: 0, ceil: 1 },
  instability_index: { label: 'Instability index' },
  sequence_length: { label: 'Sequence length', unit: 'residues', floor: 0 },
  helix_fraction: { label: 'Helix propensity', floor: 0, ceil: 1 },
  turn_fraction: { label: 'Turn propensity', floor: 0, ceil: 1 },
  sheet_fraction: { label: 'Sheet propensity', floor: 0, ceil: 1 },
}

export const EVIDENCE_EXPLAINER: Record<string, string> = {
  EC_and_GO: 'Enzyme label supported by both an EC number and a GO catalytic-activity annotation.',
  EC_only: 'Enzyme label supported by an EC number only.',
  GO_only: 'Enzyme label supported by a GO catalytic-activity annotation only.',
}

export type ChemGroup = 'hydrophobic' | 'aromatic' | 'polar' | 'positive' | 'negative' | 'special'

export const CHEM_GROUPS: { key: ChemGroup; label: string; residues: string[] }[] = [
  { key: 'hydrophobic', label: 'Hydrophobic', residues: ['A', 'V', 'L', 'I', 'M'] },
  { key: 'aromatic', label: 'Aromatic', residues: ['F', 'W', 'Y'] },
  { key: 'polar', label: 'Polar', residues: ['S', 'T', 'N', 'Q'] },
  { key: 'positive', label: 'Positive', residues: ['K', 'R', 'H'] },
  { key: 'negative', label: 'Negative', residues: ['D', 'E'] },
  { key: 'special', label: 'Special (G/P/C)', residues: ['G', 'P', 'C'] },
]

export const AA_NAMES: Record<string, string> = {
  A: 'Alanine', C: 'Cysteine', D: 'Aspartate', E: 'Glutamate', F: 'Phenylalanine',
  G: 'Glycine', H: 'Histidine', I: 'Isoleucine', K: 'Lysine', L: 'Leucine',
  M: 'Methionine', N: 'Asparagine', P: 'Proline', Q: 'Glutamine', R: 'Arginine',
  S: 'Serine', T: 'Threonine', V: 'Valine', W: 'Tryptophan', Y: 'Tyrosine',
}
