# Protein Function Classifier — Enzyme vs Non-Enzyme

Predicts whether a protein is an **enzyme** or a **non-enzyme** from its amino
acid sequence alone, using sequence-derived physicochemical features and a
consensus database-labelling strategy.

> This project evaluates multiple machine-learning approaches for
> enzyme/non-enzyme classification using sequence-derived physicochemical
> features, combined with database-informed labelling and supplementary
> biological interpretation. It does not introduce a novel algorithm and does
> not provide definitive biological annotation.

**Status: Review 1 complete** — database integration, consensus labelling and
feature engineering are built and runnable. Model training, the API and the
frontend are Review 2.

---

## 1. Biological methodology: consensus labelling

The earlier version of this project labelled proteins by EC number alone:

```
EC present -> enzyme        EC absent -> non-enzyme
```

The second rule is unsound. An EC number is an *assigned annotation*, not a
biological property. Genuine enzymes routinely lack one because curation lags
discovery, some activities do not map cleanly onto the four-level EC hierarchy,
and many proteins are simply understudied. **"No EC number" means "not
annotated", not "not an enzyme."**

This version requires two independent UniProt-queryable sources:

| Source | Term |
|---|---|
| Enzyme Commission | any EC number |
| Gene Ontology | GO:0003824, catalytic activity |

```
ENZYME      if  (EC present)  OR  (GO:0003824 present)
NON-ENZYME  if  (EC absent)  AND  (GO:0003824 absent)
```

The positive rule is a **union** — one source is enough. The negative rule is an
**intersection** — both must be silent. That asymmetry makes the negative class
deliberately harder to earn, which is exactly the property the old scheme lacked.

Every protein is tagged `EC_only`, `GO_only`, `EC_and_GO` or `neither`, and the
pipeline prints the full breakdown.

### Measured result

Complete reviewed, non-fragment human proteome (20,430 entries):

```
EC set               :  4,613        EC-only        :     11
GO catalytic set     :  5,540        GO-only        :    938
                                     Both EC + GO   :  4,602
Enzymes              :  5,551        Non-enzymes    : 14,879
```

|             | EC-only scheme | Consensus scheme |
|-------------|---------------:|-----------------:|
| Enzymes     |          4,613 |        **5,551** |
| Non-enzymes |         15,817 |           14,879 |

**938 proteins move from the negative class to the positive class** — a 20.3%
larger enzyme class, and 5.9% of the old negative class was contaminated with
true enzymes.

**On independence.** 4,602 of 4,613 EC proteins (99.76%) also carry a catalytic
GO term, so the two sources are *not* independent: the GO Annotation pipeline
assigns catalytic GO terms to EC-annotated proteins automatically via `ec2go`.
The dependence is directional — EC evidence flows into GO, not the reverse,
which is why 938 proteins have curated catalytic GO evidence and no EC number.
The claim is strictly better coverage than EC alone, not independence. The near
subsumption of EC by GO is itself a finding, and one specific to a heavily
curated organism.

### Why GO membership is resolved by query, not string match

GO:0003824 is the *root* catalytic-activity term. UniProt entries are almost
never annotated with the root directly — they carry specific descendants such as
GO:0004252 (serine-type endopeptidase activity) or GO:0016301 (kinase activity).
Searching each entry's GO list for the literal string `GO:0003824` would match
almost nothing and silently corrupt the labels.

Instead, membership is resolved with the UniProt query `go:0003824`. The UniProt
search index expands the Gene Ontology graph, so the query returns every entry
annotated with any descendant term.

### Three queries, then set arithmetic

```
EC  = accessions matching  ec:*
GO  = accessions matching  go:0003824
NEG = accessions matching  NOT ec:* AND NOT go:0003824

enzymes = EC | GO      EC-only = EC - GO
                       GO-only = GO - EC
                       both    = EC & GO
non-enzymes = NEG
```

### Sanity check

Documented non-catalytic families — transport (`keyword:KW-0813`), structural
molecule activity (`go:0005198`) and immunoglobulins — are queried separately and
their overlap with the negative set is measured. **These are not used as training
labels.** They are an independent audit that the negatives look biologically
sensible.

---

## 2. Dataset scoping

| Decision | Reason |
|---|---|
| Swiss-Prot (reviewed) only | In machine-annotated TrEMBL, a missing annotation usually means uncurated. Reviewed entries make *absence* informative. |
| Single organism (human, 9606) | Annotation depth varies by species; mixing lets the model learn organism instead of function. |
| `fragment:false` | Fragment composition is unrepresentative of the whole protein. |
| Standard residues only | Molecular weight and GRAVY are undefined for X, B, Z, J, U, O. |
| Length 50–2000 | Short peptides give unstable estimates; very long multi-domain proteins average away signal. |
| Exact duplicate sequences removed | Isoforms sharing a sequence across accessions would leak between train and test. |
| Classes balanced by downsampling | Keeps accuracy interpretable. Upsampling would place near-identical rows on both sides of the split. |

---

## 3. Features (29)

**20** amino acid composition — fraction of each standard residue, fixed
alphabetical order A..Y.

**9** global descriptors:

| Feature | Biological rationale |
|---|---|
| Sequence length | Catalysis needs a folded domain, setting a size floor |
| Molecular weight | Length-correlated but weights residue identity |
| Aromaticity | Aromatic residues are common in substrate-binding pockets |
| Instability index | Dipeptide-based stability estimate (Guruprasad et al.) |
| Isoelectric point | Catalytic sites depend on charged residues, shifting net charge |
| GRAVY | Hydropathy separates soluble globular enzymes from membrane/structural proteins |
| Helix / turn / sheet fraction | Coarse secondary-structure profile from residue propensities |

All computed with BioPython `ProteinAnalysis`.

### One implementation, shared by training and inference

`backend/app/ml/feature_engineering.py` is the single source of truth.
`training/feature_engineering.py` imports it and contains no feature maths.
Duplicated feature code would produce a model whose inputs no longer match its
training distribution — and that failure is silent.

Composition is computed from raw residue counts rather than BioPython's
percentage helper, because that helper was renamed *and* changed scale from
fractions to percentages between releases. Computing it directly keeps feature
values identical across BioPython versions and machines.

---

## 4. How to run

```bash
pip install -r backend/requirements.txt
brew install mmseqs2        # or: conda install -c conda-forge -c bioconda mmseqs2

python training/download_data.py        # UniProt REST -> data/raw/
python training/data_preprocessing.py   # cleaning + consensus labelling report
python training/feature_engineering.py  # 29 features -> data/processed/features.csv
python training/cluster_sequences.py    # MMseqs2 families -> clusters.csv
python training/train.py --learning-curve
python training/validate_kegg.py        # KEGG cross-check + false-positive audit
```

`download_data.py` needs internet access to `rest.uniprot.org`;
`validate_kegg.py` needs `rest.kegg.jp`. KEGG's API is for academic,
non-commercial use; its responses are cached in `data/raw/` and excluded from
git because KEGG data may not be redistributed.

### Homology-aware evaluation

Removing identical sequences is not enough. Paralogs share near-identical
composition, so under a random split a model can score well by recognising a
protein family it has already seen. `cluster_sequences.py` groups proteins at
40% identity / 80% coverage with MMseqs2, and `train.py` then keeps every family
entirely on one side of the train/test split and of every CV fold. If
`clusters.csv` is absent, `train.py` falls back to a random split and warns.

In a synthetic test where labels were assigned to families at random (no real
enzyme signal at all), Extra Trees scored ROC-AUC 1.000 under a random split
and 0.32 (chance) under the homology-aware split.

## 5. Current structure

```
protein-function-classifier/
├── backend/
│   ├── app/ml/feature_engineering.py   # canonical 29-feature extractor
│   └── requirements.txt
├── training/
│   ├── config.py
│   ├── download_data.py                # 3 UniProt queries + set arithmetic
│   ├── data_preprocessing.py           # cleaning + consensus labelling report
│   └── feature_engineering.py          # imports the backend extractor
├── data/{raw,processed}/
├── models/
├── docs/
│   ├── REVIEW1_VIVA_NOTES.md
│   └── GAMMA_PROMPT_REVIEW1.md
└── README.md
```

---

## 6. Planned for Review 2

Model comparison (Logistic Regression, Random Forest, Extra Trees, MLP) under
stratified 5-fold cross-validation, selected by ROC-AUC then F1 — **the winner is
measured, not assumed**. Ensembles tested but adopted only if measurably better.
Then the nearest-neighbour similar-protein finder, physicochemical comparison
dashboard, rule-based catalytic motif scan, UniProt/PDB/KEGG enrichment, FastAPI
backend and a three-file vanilla frontend.

---

## 7. Limitations

1. EC and GO are not fully independent — some GO catalytic annotations are
   electronically inferred from EC mappings.
2. Human-only scope may not generalise to other organisms.
3. Global composition discards all positional and structural information.
4. Residual label noise certainly remains in the negative class.
5. Downsampling discards real data.