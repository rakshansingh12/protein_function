# Gamma Prompt — Review 2 Presentation

## How to use

1. Go to Gamma → **Create new** → **Paste in text** → **Generate**.
2. Paste everything inside the fenced block below.
3. Settings: **Format = Presentation**, **Cards = 16**, **Text = Detailed**,
   **Image style = Minimal / illustrative diagrams**, **Theme = a light
   academic theme** (Chisel, Oasis or Vortex work well).
4. Run the post-generation checklist at the bottom before the review.

---

## The prompt

```
Create a 16-slide academic project review presentation for a university
Biological Databases course. The audience is a professor and a small review
panel. Tone: precise, scientific, understated. No marketing language, no hype,
no exclamation marks. Prefer clean diagrams and tables over decorative imagery.
Use a light background with a single accent colour throughout.

Project title: Enzyme vs Non-Enzyme Protein Classification Using Consensus
Database Labelling and Sequence-Derived Physicochemical Features

This is REVIEW 2, covering machine learning results, cross-database
validation, and the web application. Every number below is taken directly
from the project's own result files. Do not invent, round, or estimate any
number not given here — if a slide needs a figure that is not in this
prompt, leave a clearly marked placeholder instead of guessing.

Build the slides as follows.

SLIDE 1 — Title
Project title, "Review 2: Model Evaluation, Validation and Deployment",
placeholders for student name, registration number, course, and guide name.

SLIDE 2 — Recap: Consensus Labelling Result
Briefly recap the Review 1 labelling rule (ENZYME if EC present OR GO:0003824
present; NON-ENZYME only if both absent). State the measured result: after
cleaning, 19,767 reviewed human proteins, of which 11 are EC-only, 890 are
GO-only, 4,490 carry both EC and catalytic GO, and 14,376 carry neither;
balanced by downsampling to 10,782 proteins (5,391 per class) for training.
State that 890 GO-only proteins carry curated catalytic GO evidence but no EC
number, and that KEGG cannot independently confirm them because its own EC
assignments rest on the same reaction-level evidence (covered on slide 11) —
do not describe them simply as "mislabelled".

SLIDE 3 — Pipeline Overview
A left-to-right pipeline diagram: UniProt REST download -> cleaning and
consensus labelling -> 29-feature extraction -> MMseqs2 sequence clustering
-> model training (4 models + ensembles, homology-aware split) -> KEGG
cross-database validation -> AlphaFold pLDDT analysis -> FastAPI backend ->
web frontend. One line under the diagram: every stage caches its network
calls to disk and is independently re-runnable.

SLIDE 4 — Model Comparison
A table with columns Model, Test ROC-AUC (homology-aware), Test F1
(homology-aware), Test ROC-AUC (random split):
Logistic Regression: 0.7305, 0.6908, 0.7468
Random Forest: 0.8285, 0.7532, 0.8698
Extra Trees: 0.8347, 0.7607, 0.8770
Neural Network (MLP): 0.8205, 0.7460, 0.8556
Bold the Extra Trees row. Caption: "Extra Trees is selected under both
splits; the random-split column exists only to quantify homology leakage
(slide 8), not as an alternative headline number."

SLIDE 5 — Model Selection Rule
Quote the selection rule verbatim: "Ranked by cross-validated ROC-AUC, then
F1, recall, accuracy. A simpler model within 0.005 ROC-AUC of the leader is
preferred. An ensemble is adopted only if it exceeds the best individual
model by more than 0.002 ROC-AUC." State plainly that the test set is
touched exactly once, after the model is chosen on cross-validation, to
avoid circularity.

SLIDE 6 — Ensemble Decision
State that every combination of Random Forest, Extra Trees and MLP was
tuned and evaluated as a soft-voting ensemble, but none was adopted
(ensemble_selected = false in both result files). Homology-aware
cross-validated ensemble gain over the best individual model was +0.0012
ROC-AUC, below the +0.002 adoption threshold; the random-split ensemble gain
was -0.0025 (negative). Note, as an honesty point rather than a
contradiction: on the homology-aware TEST set the RF+ET+MLP ensemble scored
0.8368, higher than Extra Trees' 0.8347 test score — but the decision is
made on cross-validation before the test set is touched, so this later
number is not used to override the selection.

SLIDE 7 — Size-Only Baseline
State that a logistic regression on molecular weight and sequence length
alone reaches test ROC-AUC 0.6451 (homology-aware) / 0.6170 (random) --
meaningfully above chance (0.5), but far below the full 29-feature model.
The full model's lift over this baseline is +0.1896 (homology-aware) /
+0.2600 (random). Headline message: a large gap between class means (shown
later, slide 14 caption) is not the same as separability -- the size
baseline is the control for that claim.

SLIDE 8 — Homology Leakage
Explain that paralogs share near-identical composition, so a random
train/test split lets a model score well by recognising a protein family it
has already seen. MMseqs2 clustering at 40% identity / 80% coverage over the
10,782 proteins produced 8,022 clusters; 38.4% of proteins are in
multi-member clusters; the largest cluster has 141 members; 52 clusters mix
both labels. Repeat the model comparison table from slide 4 as a two-column
"random vs homology-aware" bar chart per model, with a "difference" value
labelled on each pair: Logistic Regression 0.0163, Random Forest 0.0414,
Extra Trees 0.0423, MLP 0.0350. State: "This gap is homology leakage being
measured, not a flaw -- it is why the homology-aware number, not the
random-split number, is the headline result."

SLIDE 9 — Learning Curve
A line chart: cross-validated ROC-AUC at training sizes 693, 1733, 3467,
5201, 6935 rising from 0.8290 to 0.8603 (values from the homology-aware
learning curve). State the last-quarter gain is only +0.0042, while training
AUC is 1.0 throughout (fully grown trees memorise their training data).
Conclusion sentence: the bottleneck looks like feature expressiveness, not
dataset size.

SLIDE 10 — Confusion Matrix
Show the homology-aware test confusion matrix for Extra Trees as a 2x2 grid:
True Negative 764, False Positive 270, False Negative 242, True Positive
814. One line underneath connecting to the next slide: the KEGG validation
below asks whether these 270 false positives are ordinary errors or
under-annotated enzymes.

SLIDE 11 — KEGG Validation and Its Limits
Explain KEGG assigns EC numbers by orthology to characterised reactions --
the same kind of evidence as UniProt EC, so it cannot independently confirm
GO-only proteins. Results: 95.2% of the dataset maps to a KEGG human gene;
of mapped enzymes, 63.3% carry a KEGG EC number (EC_and_GO 74.2%, EC_only
7/11, GO_only only 6.0%); of mapped non-enzymes, 0.3% (16 proteins) carry a
KEGG EC number (candidate mislabels). False-positive audit: only 1 of 261
test-set false positives and 0 of 686 true negatives carry a KEGG EC number
-- Fisher's exact p = 0.276, reported as INCONCLUSIVE (too few supported
cases to have statistical power), not as "no enrichment". Dedicate a boxed
callout to the PSMA3 case study: P25788, a non-catalytic 20S proteasome
alpha subunit, is correctly labelled non-enzyme by UniProt but receives
complex-level EC 3.4.25.1 from KEGG orthology -- KEGG agreement is
consistent with correct labelling, not proof of it.

SLIDE 12 — GO-Only Composition
State that of the 890 GO-only proteins, a keyword scan of protein names
found only 7.5% fall into the ATPase/GTPase/transporter "boundary" catalytic
categories often used to explain away GO-only annotations, and 65.3% match
none of the scanned keyword groups at all. Conclusion: most GO-only proteins
are not that boundary case -- they are ordinary catalytic-by-GO proteins
that simply lack a curated EC number.

SLIDE 13 — AlphaFold pLDDT Analysis
State clearly at the top: analysis only, never a model feature (circular,
since AlphaFold structures only exist for proteins already in UniProt); we
retrieve precomputed structures, we do not predict structures; pLDDT is
AlphaFold's own prediction confidence, a proxy for disorder, not disorder
itself. Report, over 2,890 proteins (890 GO-only, 1,000 EC-backed, 1,000
non-enzyme, 0% fetch failures): H1 (enzymes are more ordered than
non-enzymes) SUPPORTED -- EC-backed vs non-enzyme mean pLDDT p = 4.9e-87,
probability of superiority 0.755; H2 (instability index tracks predicted
disorder) SUPPORTED -- Spearman rho = 0.5347, p approximately 0. Note that
GO-only proteins sit between EC-backed and non-enzyme on both metrics,
closer to EC-backed.

SLIDE 14 — The Web Application
Architecture diagram: FastAPI backend (routes -> services -> ml layers)
serving a three-file vanilla HTML/CSS/JS frontend from the same origin, no
frameworks. List the features: enzyme/non-enzyme prediction with probability
and a dataset-match banner; a nearest-neighbour similar-protein finder
(training split only, similarity = 100 / (1 + distance)); a physicochemical
comparison against training-split class means for 5 properties (molecular
weight 64,286 vs 52,468 Da; instability index 45.29 vs 50.86; isoelectric
point 7.18 vs 7.45; GRAVY -0.295 vs -0.352; aromaticity 0.0857 vs 0.0773,
enzyme vs non-enzyme); a supplementary rule-based motif scan (three motifs;
Walker A / P-loop is the one with real class signal here, ratio 3.867;
serine-protease and HEXXH ratios are close to 1 and carry little class
information in this dataset); and UniProt/PDB/KEGG/AlphaFold database
enrichment for sequences that exactly match a known protein, with KEGG read
from a precomputed file rather than a live call.

SLIDE 15 — Limitations
Bulleted, honest list: homology-aware ROC-AUC (0.8347) is well below
homology-based annotation tools (~93% for tools such as ECRECer), expected
since no sequence-similarity information is used; the KEGG false-positive
audit is underpowered and inconclusive, not negative; the serine-protease
motif is a simplified 4-residue placeholder, not the official PROSITE
pattern; human-only scope; global amino-acid composition discards
positional and structural information; MLP ranking third of four models is
an expected outcome on tabular data this size, not a failure.

SLIDE 16 — Conclusions and Future Work
Conclusion: this is a rigorous study of how much sequence-derived
physicochemical signal alone can separate enzymes from non-enzymes under an
evaluation that removes homology shortcuts, combined with a corrected,
better-evidenced labelling strategy and an honest cross-database validation
-- not a competitive annotation tool, and no novel algorithm is claimed (not
patentable; extensive prior art; Indian Patents Act s.3(k)). Future work:
ESM-2 protein-language-model embeddings as a possible fifth comparison arm
(cost: interpretability); genuine cross-organism testing (train on one
species, evaluate on another); replacing the placeholder serine-protease
regex with the official PROSITE pattern; and checking how published
homology-based tools define their own negative class, for a fairer
comparison than quoting their headline accuracy alone.

Add a small footer to every slide reading "Review 2 — Biological Databases".
```

---

## After Gamma generates

Check and fix these — Gamma tends to drift:

- **Do not let any slide state or imply this model beats homology-based
  tools.** It scores well below them by design (no homology signal used).
- Confirm slide 4 and slide 8 use the exact same four ROC-AUC pairs and
  that "homology-aware" is bolded/highlighted, not the random-split column.
- Confirm the ensemble slide (6) does not conclude "so the ensemble was
  used" — it explicitly was not.
- Confirm slide 11 keeps the KEGG false-positive result labelled
  INCONCLUSIVE, not "no enrichment" or "not significant" alone.
- Confirm slide 13 states AlphaFold structures are retrieved, never
  predicted, and that pLDDT is a confidence proxy, not disorder itself.
- Trim any slide that has drifted past roughly six bullets.
- Delete any accuracy, p-value, or count that isn't one of the numbers given
  in this prompt.
