# Protein Function Classifier — Enzyme vs Non-Enzyme

Predicts whether a human protein is an **enzyme** or a **non-enzyme** from its
amino acid sequence alone, using sequence-derived physicochemical features,
a consensus database-labelling strategy, and independent cross-database
validation.

> This project evaluates multiple machine-learning approaches for
> enzyme/non-enzyme classification using sequence-derived physicochemical
> features, combined with database-informed labeling and supplementary
> biological interpretation.

**A rigorous study, not a competitive tool.** Homology-based annotation
tools score higher on this exact task (e.g. ECRECer reports ~93% accuracy on
enzyme vs non-enzyme) because they use sequence similarity to known enzymes
directly. This project deliberately avoids that shortcut in evaluation (see
§7) to measure what physicochemical composition alone can support. It
introduces no novel algorithm and is not patentable (extensive prior art;
Indian Patents Act s.3(k)). The contribution is database-informed labelling
plus an honest, homology-aware evaluation.

---

## 1. Purpose

Given a protein sequence, classify it as enzyme or non-enzyme, report a
calibrated probability, show the nearest known proteins by feature
similarity, scan for known catalytic motifs, and pull in supplementary
UniProt / PDB / KEGG / AlphaFold records when the sequence matches a known
protein. Served through a FastAPI backend and a Next.js web frontend.

---

## 2. Biological methodology: consensus labelling

Labelling by EC number alone is unsound: `EC present -> enzyme, EC absent ->
non-enzyme`. An EC number is an *assigned annotation*, not a biological
property — genuine enzymes routinely lack one because curation lags
discovery. **"No EC number" means "not annotated", not "not an enzyme."**

This project requires two independent UniProt-queryable sources instead:

| Source | Term |
|---|---|
| Enzyme Commission | any EC number |
| Gene Ontology | GO:0003824, catalytic activity |

```
ENZYME      if  (EC present)  OR  (GO:0003824 present)
NON-ENZYME  if  (EC absent)  AND  (GO:0003824 absent)
```

The positive rule is a **union** (one source is enough); the negative rule
is an **intersection** (both must be silent) — deliberately harder to earn.

**GO membership is resolved by query, not string match.** GO:0003824 is the
*root* catalytic-activity term; UniProt entries carry specific descendants
(e.g. GO:0004252, serine-type endopeptidase activity) almost exclusively.
Searching for the literal string `GO:0003824` would match almost nothing.
Membership is resolved with the UniProt query `go:0003824`, which expands
the Gene Ontology graph and returns every entry annotated with any
descendant term.

### Measured result

Complete reviewed, non-fragment human proteome (20,430 entries): EC 4,613
(EC-only 11); GO catalytic 5,540 (GO-only 938); both 4,602; neither 14,879.
After cleaning (19,767 entries, `data/processed/labeling_report.json`):
EC-only 11, GO-only 890, both 4,490, neither 14,376. Balanced by
downsampling to 10,782 (5,391 per class).

**EC and GO are not independent.** 4,602 of 4,613 EC proteins (99.76%) also
carry a catalytic GO term — the GO annotation pipeline assigns catalytic GO
terms to EC-annotated proteins automatically via `ec2go`. The dependence is
directional (EC evidence flows into GO, not the reverse), which is why 890
proteins (after cleaning) have curated catalytic GO evidence and no EC
number. The claim is strictly **better coverage** than EC alone, not
independence.

**GO-only wording.** 890 proteins carry curated catalytic GO evidence but no
EC number; the EC-only scheme would call them non-enzymes. KEGG cannot
independently confirm them, because its EC assignments rest on the same
reaction-level evidence (§8). Never described as "890 proteins were
mislabelled" on its own — see the GO-only composition analysis (§8) for what
they actually are.

---

## 3. Features (29) and their redundancy

**20** amino acid composition fractions (alphabetical A..Y) + **9** global
descriptors: sequence length, molecular weight, aromaticity, instability
index (Guruprasad et al.), isoelectric point, GRAVY, and helix/turn/sheet
fraction. All computed with BioPython `ProteinAnalysis`, implemented once in
`backend/app/ml/feature_engineering.py` (the single source of truth for both
training and inference — `training/feature_engineering.py` imports it and
contains no feature maths of its own).

The 29 features are **not independent**: aromaticity is a fixed linear
function of the F, W, Y composition fractions, and GRAVY and the
helix/turn/sheet fractions are themselves composition-weighted sums. Length,
instability index and isoelectric point contribute the most information
beyond raw composition.

---

## 4. ML methodology: four models

| Model | Why included |
|---|---|
| Logistic Regression | Linear baseline; interpretable, sets a floor for how much a nonlinear model actually buys. |
| Random Forest | Bagged decision trees; captures nonlinear feature interactions with low variance. |
| Extra Trees | Extremely randomized trees (random thresholds, not just random features); usually as strong as Random Forest with less overfitting on tabular data of this size. |
| Neural Network (MLP) | A nonlinear function approximator with no built-in tree structure, as a different inductive bias to compare against. |

All four (plus every pairwise/triple/all-four ensemble) are tuned and
evaluated under both a random split and a homology-aware split (§7).

---

## 5. Model selection

Selection rule, quoted verbatim from `models/model_results.json`:

> "Ranked by cross-validated ROC-AUC, then F1, recall, accuracy. A simpler
> model within 0.005 ROC-AUC of the leader is preferred. An ensemble is
> adopted only if it exceeds the best individual model by more than 0.002
> ROC-AUC."

Models are ranked by **cross-validated** ROC-AUC — the test set is touched
exactly once, after selection, purely to report a number. **Extra Trees is
selected under both the random split and the homology-aware split.**

---

## 6. Ensemble strategy: tested, rejected

Soft-voting ensembles of every combination of Random Forest, Extra Trees and
MLP were tuned and evaluated alongside the individual models. None was
adopted (`ensemble_selected: false` in both result files):

- Homology-aware split: best ensemble gain over the best individual model
  was +0.0012 ROC-AUC (cross-validated) — under the 0.002 threshold.
- Random split: ensemble gain was **negative** (-0.0025).
- On the homology-aware **test** set, the RF+ET+MLP ensemble actually scored
  highest of everything (0.8368 vs Extra Trees' 0.8347) — but selection is
  decided on cross-validation, not on the test set, so this is not used to
  override the rule. Reporting it after the fact and picking it anyway would
  be exactly the kind of test-set leakage the split is designed to prevent.

**Never claimed: that an ensemble is better, that the classifier gives
definitive annotation, or that a motif proves enzymatic function.**

---

## 7. Evaluation integrity

**A large gap in class means is not separability.** A logistic regression on
molecular weight and sequence length alone (`size_baseline` in the result
files) already reaches test ROC-AUC 0.6451 (homology-aware) / 0.6170
(random) — meaningfully above chance, but far below the full model. The full
29-feature model's lift over this baseline is +0.1896 (homology-aware) /
+0.2600 (random).

**Homology leakage.** Removing exact-duplicate sequences is not enough:
paralogs share near-identical composition, so a random split lets a model
score well by recognising a protein family it has already seen rather than
learning enzyme-vs-non-enzyme signal. `cluster_sequences.py` groups the
10,782 proteins at 40% identity / 80% coverage with MMseqs2 (8,022 clusters;
38.4% of proteins in multi-member clusters; largest cluster 141; 52 clusters
mix both labels), and `train.py` keeps every cluster entirely on one side of
the train/test split and of every CV fold.

| Model | ROC-AUC (random) | ROC-AUC (homology-aware) | Difference |
|---|---|---|---|
| Logistic Regression | 0.7468 | 0.7305 | 0.0163 |
| Random Forest | 0.8698 | 0.8285 | 0.0414 |
| Extra Trees | 0.8770 | 0.8347 | 0.0423 |
| Neural Network (MLP) | 0.8556 | 0.8205 | 0.0350 |

(Full table with ensembles in `docs/RESULTS_LOG.md`, §2.) The gap
(~0.04 ROC-AUC for the flexible tree models, smaller for the linear model)
is homology leakage being quantified, not a bug — this is why **homology-aware
ROC-AUC 0.8347 (Extra Trees) is the headline number**, not the random-split
0.8770.

**Homology-aware confusion matrix** (Extra Trees, test set): TN 764, FP 270,
FN 242, TP 814.

**Learning curve:** cross-validated ROC-AUC rises from 0.829 to 0.860 across
the training-size sweep; the last-quarter gain is only +0.0042, while
training-set AUC is 1.0 throughout (fully grown trees memorise their
training data) — indicating the bottleneck is feature expressiveness, not
dataset size.

---

## 8. KEGG validation and its limits

KEGG assigns EC numbers to human genes through its own orthology system
(KEGG Orthology): a gene inherits an EC number when it belongs to an
ortholog group containing characterised enzymes. This checks the EC-backed
labels across species, but it rests on the same reaction-level evidence as
UniProt EC, so **it cannot independently confirm GO-only enzymes** — low
KEGG support for GO-only proteins is expected by construction.

Results (`training/validate_kegg.py`, full output in `docs/RESULTS_LOG.md`
§3/§5): 95.2% of the dataset maps to a KEGG human gene. Of mapped enzymes,
63.3% carry a KEGG EC number (EC_and_GO 74.2%, EC_only 7/11, **GO_only only
6.0%** — consistent with the "cannot independently confirm" limitation
above, not proof the GO-only group is wrong). Of mapped non-enzymes, only
0.3% (16 proteins) carry a KEGG EC number — these are candidate mislabels,
listed in `data/processed/kegg_candidate_mislabels.csv`.

**False-positive audit.** Are the model's false positives (proteins labelled
non-enzyme that the model calls enzyme) hidden enzymes the annotation
missed? Only 1 of 261 test-set false positives, and 0 of 686 true negatives,
carry a KEGG EC number — **too few to test** (Fisher's exact p = 0.276,
INCONCLUSIVE by construction: with `MIN_KEGG_SUPPORTED_FOR_TEST = 10` as the
power floor, this result is reported as inconclusive rather than as "no
enrichment", which would overstate what an underpowered test can show).

**GO-only composition** (`training/motif_stats.py`... `go_only_breakdown`,
§6 in RESULTS_LOG): by protein name, only 7.5% of the 890 GO-only proteins
fall into the ATPase/GTPase/transporter "boundary" categories often cited as
borderline-catalytic; 65.3% match none of the scanned keyword groups at all.
Most GO-only proteins are not that boundary case — they are simply
catalytic-by-GO proteins without a curated EC assignment.

**PSMA3 case study.** P25788 (PSMA3, a non-catalytic 20S proteasome alpha
subunit) receives complex-level EC 3.4.25.1 from KEGG orthology, while
UniProt correctly labels it non-enzyme — a concrete illustration of why KEGG
agreement is *consistent with* the negative class, not proof of it.

---

## 9. AlphaFold pLDDT analysis (analysis only)

**AlphaFold is never a model feature** — it is retrieved only for proteins
already in UniProt, so using it as a training feature would be circular. We
**retrieve** precomputed structures from AlphaFold DB; we never claim to
predict 3D structures ourselves. pLDDT is AlphaFold's own prediction
confidence, a *proxy* for structural disorder, not disorder itself.

Two hypotheses were tested (`training/alphafold_analysis.py`, full output in
`docs/RESULTS_LOG.md` §7), each over 2,890 proteins (890 GO-only, 1,000
EC-backed, 1,000 non-enzyme, 0% fetch failures):

- **H1 (enzymes are more ordered than non-enzymes): SUPPORTED.** EC-backed
  proteins have higher mean pLDDT than non-enzymes (p = 4.9e-87, probability
  of superiority 0.755) and a lower fraction of very-low-confidence residues
  (p = 8.0e-42).
- **H2 (instability index tracks predicted disorder): SUPPORTED.** Spearman
  rho = 0.5347 between instability index and fraction of very-low-pLDDT
  residues (p ≈ 0, n = 2,890).
- GO-only proteins sit between EC-backed and non-enzyme proteins on both
  metrics, closer to EC-backed — consistent with GO-only being mostly
  genuine, folded catalytic proteins rather than a distinct disordered
  group.

---

## 10. Similar-protein finder

`NearestNeighbors(n_neighbors=5, metric="euclidean")` fit once on the
StandardScaler-scaled training-split features (search space excludes the
test split, so it can never leak test proteins into a result).
`similarity = 100 / (1 + distance)`: simple, monotonic, bounded in (0, 100],
where 100 means identical scaled features — chosen for interpretability over
a more exotic kernel.

---

## 11. Physicochemical comparison

For 5 of the 29 features (isoelectric point, GRAVY, molecular weight,
aromaticity, instability index), the API returns the input protein's value
alongside the training-split class means ± SD (`models/class_stats.json`,
n = 4,335 enzymes / 4,357 non-enzymes). Measured class means: molecular
weight 64,286 vs 52,468 Da; instability index 45.29 vs 50.86; isoelectric
point 7.18 vs 7.45; GRAVY -0.295 vs -0.352; aromaticity 0.0857 vs 0.0773.
The frontend renders these as horizontal bars (GRAVY centred at zero, since
it can be negative) — a large gap in a mean is a description, not proof of
separability (§7).

---

## 12. Motif scanning

Three short, low-specificity regex patterns (`backend/app/services/motif_service.py`),
reported as a **supplementary, rule-based check that never overrides the ML
prediction**:

| Motif | Pattern | Notes |
|---|---|---|
| Serine protease-related (simplified) | `[DES]-[ST]-x-[LIVM]` | A 4-residue placeholder, **not** the official PROSITE pattern (TODO), and matches most proteins by chance — low specificity. |
| HEXXH zinc-binding | `H-E-x-x-H` | Characteristic of zinc metalloproteases; the two histidines coordinate the catalytic zinc. |
| Walker A / P-loop | `[AG]-x(4)-G-K-[ST]` | Phosphate-binding loop in ATP/GTP-binding proteins. |

`training/motif_stats.py` measures how much each motif actually separates
the classes in this dataset (`models/motif_stats.json`, full output in
`docs/RESULTS_LOG.md` §8): Serine protease-related (ratio 1.078) and HEXXH
(ratio 1.179) appear at similar rates in both classes and carry **little
class information here**; Walker A / P-loop (ratio 3.867) is the one
informative motif of the three.

---

## 13. Database enrichment

For sequences that exactly match a known accession (SHA-256 lookup against
`models/sequence_index.json`, all 20,352 unique cleaned sequences), the API
pulls supplementary records: UniProt (protein name, organism, subcellular
location, PDB cross-references), AlphaFold (mean pLDDT, fraction very-low
confidence, link), and KEGG (genes, EC, named pathways — from the
precomputed `models/kegg_pathways.json`, **never a live KEGG call**, since
KEGG times out on this network). Every external source is isolated: a
timeout, HTTP error or malformed response degrades that one field to `null`
rather than failing the request (see `docs/API.md`).

---

## 14. Limitations

1. EC and GO are not independent (§2) — claim better coverage, not
   independent confirmation.
2. Human-only scope; may not generalise to other organisms.
3. Global amino-acid composition discards all positional and structural
   information.
4. Homology-aware ROC-AUC (0.8347) is meaningfully below random-split
   (0.8770) and below homology-based annotation tools (~93% for ECRECer) —
   expected, since this model uses no sequence-similarity information at
   all.
5. The false-positive KEGG audit (§8) is underpowered (1 supported
   false-positive) and explicitly reported as inconclusive, not negative.
6. The serine-protease motif is a low-specificity 4-residue placeholder, not
   the official PROSITE pattern.
7. MLP ranking third of four models is expected on tabular data of this
   size, not a failure of the architecture.
8. RDKit was declined (a small-molecule cheminformatics toolkit, not suited
   to whole-protein sequence features). ESM-2 protein-language-model
   embeddings are future work — a possible fifth comparison arm, at the cost
   of interpretability.

---

## 15. How to run

```bash
pip install -r backend/requirements.txt
brew install mmseqs2        # or: conda install -c conda-forge -c bioconda mmseqs2

# Full pipeline, in order (data/processed/ and models/ are already built and
# checked in for this dataset; re-running is normally unnecessary):
python training/download_data.py          # UniProt REST -> data/raw/
python training/data_preprocessing.py     # cleaning + consensus labelling
python training/feature_engineering.py    # 29 features -> data/processed/features.csv
python training/cluster_sequences.py      # MMseqs2 families -> clusters.csv
python training/train.py --learning-curve # 4 models + ensembles, homology-aware split
python training/validate_kegg.py          # KEGG cross-check + false-positive audit
python training/alphafold_analysis.py     # pLDDT disorder analysis (H1/H2)
python training/build_sequence_index.py   # accession lookup by sequence hash
python training/build_kegg_pathways.py    # precomputed per-accession KEGG map
python training/motif_stats.py            # class match rates for each motif

# Build the frontend (Next.js, once and after UI changes)
cd frontend && npm install && npm run build && cd ..

# Run the app (serves the API and frontend/out/ on one origin)
uvicorn backend.app.main:app --reload
# open http://127.0.0.1:8000/

# Optional: live-reload UI development (with uvicorn running on :8000)
cd frontend && npm run dev   # open http://localhost:3000/, /api is proxied

# Tests
pytest backend/tests -q
```

`download_data.py` needs `rest.uniprot.org`; `validate_kegg.py` and
`build_kegg_pathways.py` need `rest.kegg.jp` (KEGG is slow on some networks
— use `curl -4` if `requests` times out); `alphafold_analysis.py` needs
`alphafold.ebi.ac.uk`. All downloaded tables are cached in `data/raw/`.

---

## 16. Data licences

- **UniProt** data is CC BY 4.0.
- **AlphaFold DB** structure predictions are CC BY 4.0.
- **KEGG** REST API access is for academic, non-commercial use only; KEGG
  responses are cached locally in `data/raw/` and are excluded from git
  (`.gitignore`) — KEGG data is not redistributed.
