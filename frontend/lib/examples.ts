// Static example content for the UI. No numbers here are made up: the motif
// class rates below are copied verbatim from models/motif_stats.json, and the
// explanation text from backend/app/services/motif_service.py.
import type { MotifMatch } from './types'

export const EXAMPLE_FASTA = `>sp|P00918|CAH2_HUMAN Carbonic anhydrase 2
MSHHWGYGKHNGPEHWHKDFPIAKGERQSPVDIDTHTAKYDPSLKPLSVSYDQATSLRI
LNNGHAFNVEFDDSQDKAVLKGGPLDGTYRLIQFHFHWGSLDGQGSEHTVDKKKYAAEL
HLVHWNTKYGDFGKAVQQPDGLAVLGIFLKVGSAKPGLQKVVDVLDSIKTKGKSADFTN
FDPRGLLPESLDYWTYPGSLTTPPLLECVTWIVLKEPISVSSEQVLKFRKLNFNGEGEP
EELMVDNWRPAQPLKNRQIKASFK`

// Shown only as an illustration of how a motif hit is displayed, when the
// analysed sequence itself has no hits. Position/match are illustrative.
export const EXAMPLE_MOTIF_MATCH: MotifMatch = {
  name: "Serine protease-related (simplified)",
  start: 302,
  end: 305,
  match: 'DSVL',
  explanation: "A simplified approximation of the serine protease active-site motif. Official PROSITE patterns or ScanProsite should be preferred: this 4-residue pattern matches most proteins by chance and has low specificity.",
  class_rates: {
    enzyme_hits: 4574,
    enzyme_total: 5391,
    enzyme_pct: 0.8484511222407717,
    non_enzyme_hits: 4245,
    non_enzyme_total: 5391,
    ratio_enzyme_over_non_enzyme: 1.0775029446407538,
  },
}
