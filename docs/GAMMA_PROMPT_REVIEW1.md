# Gamma Prompt — Review 1 Presentation

## How to use

1. Go to Gamma → **Create new** → **Paste in text** → **Generate**.
2. Paste everything inside the fenced block below.
3. Settings: **Format = Presentation**, **Cards = 12**, **Text = Detailed**,
   **Image style = Minimal / illustrative diagrams**, **Theme = a light
   academic theme** (Chisel, Oasis or Vortex work well).
4. After generating, fill in the four `[ ]` placeholders on slide 6 with the real
   numbers your pipeline prints. **Do this before the review** — empty brackets
   on screen look worse than modest numbers.

---

## The prompt

```
Create a 12-slide academic project review presentation for a university
Biological Databases course. The audience is a professor and a small review
panel. Tone: precise, scientific, understated. No marketing language, no hype,
no exclamation marks. Prefer clean diagrams and tables over decorative imagery.
Use a light background with a single accent colour throughout.

Project title: Enzyme vs Non-Enzyme Protein Classification Using Consensus
Database Labelling and Sequence-Derived Physicochemical Features

This is REVIEW 1, covering problem definition, database integration, labelling
methodology, and feature engineering. Machine learning results are explicitly
deferred to Review 2 — do not invent or present any accuracy figures.

Build the slides as follows.

SLIDE 1 — Title
Project title, "Review 1: Database Integration and Consensus Labelling",
placeholders for student name, registration number, course, and guide name.

SLIDE 2 — Problem Statement
Predicting protein function experimentally is slow and expensive, while sequence
data accumulates far faster than functional annotation. Objective: determine
whether a protein is an enzyme or a non-enzyme using its amino acid sequence
alone, with no homology search and no structural data. Frame the scientific
question as: do global physicochemical properties carry enough signal to
separate catalytic from non-catalytic proteins.

SLIDE 3 — The Flaw in the Original Approach
The earlier version of this project labelled proteins using EC number presence
alone: EC present means enzyme, EC absent means non-enzyme. Explain that the
second rule is unsound, because an EC number is an assigned annotation rather
than a biological property. Enzymes can lack an EC number due to curation lag,
activities that do not map cleanly onto the four-level EC hierarchy, and simple
lack of study. Conclude with the key line: "No EC number means not annotated,
not not an enzyme." Add that training on this rule teaches the model to
reproduce annotation gaps instead of biology, because mislabelled true enzymes
sitting in the negative class distort the decision boundary.

SLIDE 4 — Consensus Labelling Strategy
Present the rule as a clear logic block:
  ENZYME     if (EC number present) OR (GO:0003824 catalytic activity present)
  NON-ENZYME if (EC number absent) AND (GO:0003824 absent)
Emphasise the asymmetry: the positive rule is a union so one source suffices,
while the negative rule is an intersection so both sources must be silent. State
that this makes the negative class deliberately harder to earn. Note that every
protein is tagged as EC-only, GO-only, both, or neither.

SLIDE 5 — Resolving GO:0003824 Correctly
This is a technical-depth slide. Explain that GO:0003824 is the root
catalytic-activity term, and that UniProt entries are almost never annotated
with the root directly — they carry specific descendant terms such as GO:0004252
serine-type endopeptidase activity or GO:0016301 kinase activity. Therefore
string-matching the literal ID GO:0003824 against each entry would match almost
nothing and silently corrupt the labels. The solution is to resolve membership
using the UniProt query go:0003824, because the UniProt search index expands the
Gene Ontology graph and returns all descendant terms. Include a small tree
diagram showing GO:0003824 as a parent node with three example child terms.

SLIDE 6 — Three Queries, Then Set Arithmetic
Show the three UniProt queries and the set logic derived from them:
  EC set  = entries matching ec:*
  GO set  = entries matching go:0003824
  NEG set = entries matching NOT ec:* AND NOT go:0003824
  enzymes = EC union GO, EC-only = EC minus GO, GO-only = GO minus EC,
  both = EC intersect GO, non-enzymes = NEG
Include a two-circle Venn diagram of the EC and GO sets with the three regions
labelled EC-only, both, and GO-only, plus a separate box outside for
non-enzymes. Add a results table with these rows and blank value cells for the
student to fill in: EC-only, GO-only, Both EC and GO, Neither, Final enzyme
count, Final non-enzyme count.

SLIDE 7 — Why the GO-Only Count Matters
State that the GO-only count is precisely the number of proteins the earlier
EC-only scheme would have mislabelled as non-enzymes. Stress that this is a
measured, reproducible quantity rather than a claim, and that it is the
quantitative justification for the entire labelling redesign. Leave a large
placeholder for the number.

SLIDE 8 — Dataset Scoping and Cleaning
Present each decision alongside its justification in a two-column table:
Swiss-Prot reviewed entries only, because in machine-annotated TrEMBL a missing
annotation usually means uncurated, so only reviewed entries make absence
informative. Single organism, human taxon ID 9606, because annotation depth
varies across species and mixing them would let the model learn organism instead
of function. Fragments excluded, because fragment composition is unrepresentative.
Non-standard residues X, B, Z, J, U and O removed, because molecular weight and
hydropathy are undefined for ambiguous codes. Length window of 50 to 2000
residues. Exact duplicate sequences removed to prevent train/test leakage from
isoforms sharing a sequence. Classes balanced by downsampling rather than
upsampling, because duplicating rows would place near-identical proteins on both
sides of the split.

SLIDE 9 — Independent Sanity Check
Explain that documented non-catalytic families are queried separately —
transport proteins via keyword KW-0813, structural molecule activity via
GO:0005198, and immunoglobulins — and that the overlap between these families
and the negative set is measured. State clearly that these families are NOT used
as training labels; they serve only as an external audit that the negatives look
biologically sensible.

SLIDE 10 — Feature Engineering: 29 Features
State the composition as 20 plus 9. The 20 are amino acid composition, the
fraction of each standard residue in fixed alphabetical order. The 9 are
sequence length, molecular weight, aromaticity, instability index, isoelectric
point, GRAVY hydropathy, and helix, turn and sheet fractions. All are computed
with BioPython ProtParam. Give the biological rationale in a compact table:
catalysis requires a folded domain which sets a size floor; aromatic residues
are common in substrate-binding pockets; catalytic sites depend on charged
residues which shifts isoelectric point; hydropathy separates soluble globular
enzymes from membrane and structural proteins; and amino acid composition itself
carries signal because enzymes are enriched in catalytic residues such as
histidine, cysteine, aspartate, glutamate and serine.

SLIDE 11 — Train and Inference Consistency
Explain that there is exactly one feature-extraction implementation, located in
the backend, and that the training pipeline imports it rather than
reimplementing it. Note that duplicated feature code would produce a model whose
inputs no longer match its training distribution, and that this failure is
silent — nothing crashes, the predictions simply become wrong. Add a short note
that amino acid composition is computed from raw residue counts rather than a
library helper, because that helper was renamed and its scale changed from
fractions to percentages between BioPython releases, so computing it directly
keeps feature values identical across versions and machines.

SLIDE 12 — Current Status and Review 2 Plan
Two columns. Completed: UniProt REST integration with cursor pagination and
retry handling, consensus labelling with full evidence-class reporting, cleaning
and leakage prevention, 29-feature extraction verified end to end, and project
structure established. Planned for Review 2: comparison of Logistic Regression,
Random Forest, Extra Trees and a small MLP neural network under stratified
five-fold cross-validation; model selection by ROC-AUC with F1 as the secondary
metric; ensemble experiments adopted only if measurably better; a nearest
neighbour similar-protein finder; a physicochemical comparison dashboard; a
rule-based catalytic motif scan; UniProt, PDB and KEGG enrichment; and a FastAPI
backend with a plain HTML, CSS and JavaScript frontend. Add one closing line
stating that the final algorithm will be selected from measured validation
performance rather than assumed in advance.

Add a small footer to every slide reading "Review 1 — Biological Databases".
```

---

## After Gamma generates

Check and fix these — Gamma tends to drift:

- **Delete any invented accuracy or performance numbers.** Review 1 has no ML
  results. If a slide shows "94% accuracy", remove it. Presenting a fabricated
  metric is the fastest way to lose credibility in a viva.
- Confirm the Venn diagram on slide 6 has the correct three regions.
- Trim any slide that has drifted past roughly six bullets.
- Fill the blank cells on slides 6 and 7 with real pipeline output.
