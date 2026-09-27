# Results Log

## 1. Sequence clustering

```
Proteins                    : 10782
Clusters                    : 8022
Singletons                  : 6645
Largest cluster             : 141
Proteins in multi-member    : 4137 (38.4%)
Clusters mixing both labels : 52
```

## 2. Random vs homology-aware split

| Model | ROC-AUC (random) | ROC-AUC (homology-aware) | Difference |
|---|---|---|---|
| Logistic Regression | 0.7468 | 0.7305 | 0.0163 |
| Random Forest | 0.8698 | 0.8285 | 0.0414 |
| Extra Trees | 0.8770 | 0.8347 | 0.0423 |
| Neural Network (MLP) | 0.8556 | 0.8205 | 0.0350 |
| Ensemble (RF + ET) | 0.8757 | 0.8338 | 0.0420 |
| Ensemble (ET + MLP) | 0.8729 | 0.8346 | 0.0383 |
| Ensemble (RF + MLP) | 0.8714 | 0.8337 | 0.0377 |
| Ensemble (RF + ET + MLP) | 0.8759 | 0.8368 | 0.0390 |
| Ensemble (all four) | 0.8694 | 0.8337 | 0.0357 |

Difference = ROC-AUC (random) − ROC-AUC (homology-aware).

**Best model**
- `model_results_random_split.json` (random split): Extra Trees
- `model_results.json` (split_mode = homology_aware): Extra Trees

**Size baseline**
- Random split: test ROC-AUC = 0.6170, lift_of_full_model = 0.2600
- Homology-aware split: test ROC-AUC = 0.6451, lift_of_full_model = 0.1896

## 3. KEGG validation

```
========================================================================
KEGG CROSS-DATABASE VALIDATION
========================================================================
Downloading mappings (cached after the first successful run):
  cached  uniprot_kegg_xref.tsv
  cached  kegg_hsa_enzyme.tsv
  cached  kegg_hsa_pathway.tsv

UniProt entries linked to KEGG        : 19079
KEGG human genes with an EC number    : 3519
KEGG human genes in any pathway       : 9423

========================================================================
QUESTION 1 — DO OUR LABELS AGREE WITH KEGG?
========================================================================
Proteins in dataset          : 10782
Mapped to a KEGG human gene  : 10269 (95.2%)
------------------------------------------------------------------------
Our enzymes (mapped)         : 5270
  with KEGG EC number        : 3337 (63.3%)
Our non-enzymes (mapped)     : 4999
  with KEGG EC number        : 16 (0.3%)  <- candidate mislabels

KEGG EC support by evidence class (enzymes only):
  EC_and_GO     3280 / 4421  (74.2%)
  EC_only          7 / 11    (63.6%)
  GO_only         50 / 838   (6.0%)

In at least one KEGG metabolic pathway:
  enzyme        1590 / 5270  (30.2%)
  non_enzyme      45 / 4999  (0.9%)

========================================================================
QUESTION 2 — ARE THE MODEL'S FALSE POSITIVES REALLY ERRORS?
========================================================================
Among test-set proteins labelled non-enzyme and mapped to KEGG:
  Model said ENZYME     (false positives) :    1 / 261  have KEGG EC (0.4%)
  Model said NON-ENZYME (true negatives)  :    0 / 686  have KEGG EC (0.0%)
------------------------------------------------------------------------
Fisher's exact test (one-sided): odds ratio = inf, p = 2.76e-01

Interpretation: no significant enrichment. The false positives
look like ordinary model errors rather than hidden enzymes.

Top candidates (model-confident, KEGG-supported):
  P25788       p(enzyme)=0.723  KEGG EC 3.4.25.1
Full list -> /Users/rakshansingh/Downloads/protein-function-classifier/data/processed/kegg_candidate_mislabels.csv
Check a few on uniprot.org before claiming anything about them.

Saved -> /Users/rakshansingh/Downloads/protein-function-classifier/data/processed/kegg_validation.json
```

## 4. Files changed in this session

- `training/config.py` (overwritten with updated version from `~/Downloads/config.py`)
- `training/validate_kegg.py` (overwritten with updated version from `~/Downloads/validate_kegg.py`)
- `logs/backup/config.py.bak` (created)
- `logs/backup/validate_kegg.py.bak` (created)
- `data/raw/kegg_hsa_enzyme.tsv` (created)
- `data/raw/kegg_hsa_pathway.tsv` (created)
- `logs/validate_kegg.log` (created)
- `logs/cluster_summary.log` (created)
- `docs/RESULTS_LOG.md` (created)

Not on the allowed-files list but written as a side effect of running `training/validate_kegg.py` in Step 4 (flagged and confirmed with the user before continuing):
- `data/processed/kegg_validation.json` (created by the script)
- `data/processed/kegg_candidate_mislabels.csv` (created by the script)

## 5. KEGG validation (corrected interpretation)

```
========================================================================
KEGG CROSS-DATABASE VALIDATION
========================================================================
Downloading mappings (cached after the first successful run):
  cached  uniprot_kegg_xref.tsv
  cached  kegg_hsa_enzyme.tsv
  cached  kegg_hsa_pathway.tsv

UniProt entries linked to KEGG        : 19079
KEGG human genes with an EC number    : 3519
KEGG human genes in any pathway       : 9423

========================================================================
QUESTION 1 — DO OUR LABELS AGREE WITH KEGG?
========================================================================
Proteins in dataset          : 10782
Mapped to a KEGG human gene  : 10269 (95.2%)
------------------------------------------------------------------------
Our enzymes (mapped)         : 5270
  with KEGG EC number        : 3337 (63.3%)
Our non-enzymes (mapped)     : 4999
  with KEGG EC number        : 16 (0.3%)  <- candidate mislabels

KEGG EC support by evidence class (enzymes only):
  EC_and_GO     3280 / 4421  (74.2%)
  EC_only          7 / 11    (63.6%)
  GO_only         50 / 838   (6.0%)
  Note: KEGG assigns EC numbers through orthology to characterised
  reactions, the same kind of evidence behind UniProt EC. Low KEGG
  support for GO-only proteins is therefore expected by construction,
  and does not by itself show that they are not enzymes.

In at least one KEGG metabolic pathway:
  enzyme        1590 / 5270  (30.2%)
  non_enzyme      45 / 4999  (0.9%)

========================================================================
QUESTION 2 — ARE THE MODEL'S FALSE POSITIVES REALLY ERRORS?
========================================================================
Among test-set proteins labelled non-enzyme and mapped to KEGG:
  Model said ENZYME     (false positives) :    1 / 261  have KEGG EC (0.4%)
  Model said NON-ENZYME (true negatives)  :    0 / 686  have KEGG EC (0.0%)
------------------------------------------------------------------------
Fisher's exact test (one-sided): odds ratio = inf, p = 2.76e-01

Interpretation: INCONCLUSIVE. Only 1 labelled non-enzyme(s) in the test
set carry any KEGG EC number, so this test has almost no power to
detect enrichment either way. KEGG's EC assignments track the same
kind of reaction-level evidence as UniProt EC, so a protein missing
an EC number in UniProt usually lacks one in KEGG too. KEGG cannot
tell us whether these false positives are hidden enzymes.

Top candidates (model-confident, KEGG-supported):
  P25788       p(enzyme)=0.723  KEGG EC 3.4.25.1
Full list -> /Users/rakshansingh/Downloads/protein-function-classifier/data/processed/kegg_candidate_mislabels.csv
Check a few on uniprot.org before claiming anything about them.

Saved -> /Users/rakshansingh/Downloads/protein-function-classifier/data/processed/kegg_validation.json
```

## 6. GO-only composition

```
GO-only proteins: 890

Keyword groups (overlapping; will not sum to the total):
  ATPase / ABC               12  (1.3%)
  GTPase / Ras / Rab         50  (5.6%)
  Transporter / channel       5  (0.6%)
  Helicase                    1  (0.1%)
  Kinase                     34  (3.8%)
  Ubiquitin / ligase         39  (4.4%)
  Name ends in -ase         244  (27.4%)
  Matches no group          581  (65.3%)

ATPase OR GTPase OR transporter: 67 (7.5%)

Random sample of 25 names (seed 42):
   UNC5C-like protein
   Putative inactive deoxyuridine 5'-triphosphate nucleotidohydrolase-like protein FLJ16323
   E3 ubiquitin-protein ligase RNFT2
   Mitochondrial ribosome-associated GTPase 1
   Regulator of G protein signaling 4
   Carbonic anhydrase-related protein
   Glutaredoxin-1
   Putative FK506-binding protein 9-like protein
   Electron transfer flavoprotein subunit alpha, mitochondrial
   Unconventional myosin-Ig
   Ephrin-A3
   Kinesin-like protein KIF2A
   Neuronal acetylcholine receptor subunit alpha-4
   Leucine-rich repeat and guanylate kinase domain-containing protein
   ADP-ribosylation factor-like protein 13A
   Regulator of G protein signaling 19
   Putative ADP-ribosylation factor-like protein 17B
   DNA repair protein XRCC1
   GH3 domain-containing protein
   Zinc finger protein 738
   Queuine tRNA-ribosyltransferase accessory subunit 2
   ADP-ribosylation factor-like protein 5A
   Tubulin beta chain
   DNA-directed RNA polymerase II subunit RPB11-b2
   Casein kinase II subunit beta

Random sample of 15 names matching NO group (seed 42):
   Secernin-2
   Kinesin-like protein KIF13A
   Putative elongation factor 1-alpha-like 3
   Haptoglobin-related protein
   Kinesin-like protein KIF3C
   DNA-directed RNA polymerases I, II, and III subunit RPABC5
   Kinesin-like protein KIFC2
   Cytochrome b
   Thioredoxin domain-containing protein 17
   ADP-ribosylation factor-like protein 6
   Regulator of G protein signaling 14
   Septin-10
   F-box only protein 24
   Vasopressin-neurophysin 2-copeptin
   Regulator of G protein signaling 20

Saved -> data/processed/go_only_proteins.csv
```

Most GO-only proteins do not fall into the ATPase/GTPase/transporter boundary categories (7.5%); by name, the group is dominated by other catalytic or uncharacterised proteins. 65.3% of GO-only proteins match none of the keyword groups scanned.
