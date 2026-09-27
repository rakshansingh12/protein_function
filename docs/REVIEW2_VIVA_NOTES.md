# Review 2 — Viva Preparation Notes

Everything below is what you should be able to say without reading from a screen.

---

## 1. The one-sentence pitch

> "I predict whether a human protein is an enzyme or a non-enzyme from its
> amino acid sequence alone, using sequence-derived physicochemical
> features, and I evaluate it under a homology-aware split so the reported
> score isn't inflated by protein families the model has already seen."

If the examiner only remembers one thing: **homology-aware evaluation**, not
the model architecture.

---

## 2. What changed since Review 1

Review 1 built the database integration and consensus labelling. Review 2
adds everything downstream of that:

- Four models (Logistic Regression, Random Forest, Extra Trees, MLP) plus
  every ensemble combination, compared under stratified cross-validation.
- **Homology-aware train/test split** (MMseqs2 clustering) as the headline
  evaluation, with the earlier random split kept only to quantify leakage.
- A size-only baseline (molecular weight + length) to show a large class-mean
  gap is not the same as separability.
- Independent cross-database validation against KEGG, with a corrected,
  power-aware interpretation of the false-positive test.
- An AlphaFold pLDDT disorder analysis (two hypotheses, analysis only, never
  a model feature).
- Three helper artefacts (sequence index, KEGG pathway map, motif class
  statistics) plus a FastAPI backend and a three-file vanilla frontend that
  serves predictions, a similar-protein finder, a physicochemical comparison,
  a motif scan, and database enrichment.

---

## 3. Numbers to memorise

| Quantity | Value |
|---|---|
| Balanced dataset | 10,782 proteins (5,391 / class) |
| GO-only proteins (after cleaning) | 890 |
| EC-and-GO overlap | 99.76% of EC proteins |
| Best model | Extra Trees |
| **Headline ROC-AUC (homology-aware, test)** | **0.8347** |
| ROC-AUC (random split, same model) | 0.8770 |
| Homology leakage gap | ~0.04 (flexible models), 0.0163 (Logistic Regression) |
| Size-only baseline ROC-AUC (homology-aware) | 0.6451 |
| Lift of full model over size baseline | +0.1896 |
| MMseqs2 clusters | 8,022 (38.4% of proteins in multi-member clusters) |
| Clusters mixing both labels | 52 |
| Homology-aware confusion matrix | TN 764, FP 270, FN 242, TP 814 |
| KEGG mapping rate | 95.2% |
| KEGG false-positive test | 1/261 supported — INCONCLUSIVE |
| AlphaFold H1 / H2 | both SUPPORTED |
| Informative motif | Walker A / P-loop (ratio 3.867) |

---

## 4. Methodology explanations (quick reference)

**Why these four models?** Logistic Regression is a linear, interpretable
floor. Random Forest and Extra Trees are two bagged-tree variants that
capture nonlinear interactions; Extra Trees adds extra randomness at split
selection, which usually helps generalisation on tabular data this size. MLP
is a different inductive bias entirely (no tree structure) to see whether a
neural approach finds signal the trees miss.

**Why is the selection rule "CV first, test once"?** Ranking models on the
test set and then reporting that same test score is circular — you'd be
measuring how well you can pick the best of many noisy estimates, not how
well the winning model generalises. Cross-validated ROC-AUC (then F1,
recall, accuracy as tie-breakers) selects the model; the test set is touched
exactly once, after the choice is locked in.

**Why was the ensemble rejected even though it scored higher on test?**
Because "higher on test" is exactly the number you're not allowed to use to
make the decision (see above). On cross-validation, the best ensemble only
beat Extra Trees by +0.0012 ROC-AUC — under the pre-registered +0.002
threshold for adopting the extra complexity. Its 0.8368 test score is real,
but picking it *because of* that number would be the same circularity, just
one comparison later.

---

## 5. Live demo script

```bash
uvicorn backend.app.main:app --reload
# open http://127.0.0.1:8000/
```

1. Click **Load example** (Carbonic anhydrase 2, P00918) → **Predict**. Point
   at: the ENZYME banner and probability; the "matches a known protein"
   banner and the training-split notice; the model performance table with
   Extra Trees highlighted; the physicochemical comparison bars.
2. Clear the box, paste **Matrix metalloproteinase-19 (Q99542)**'s sequence
   (from `data/processed/proteins_labeled.csv`) → **Predict**. Point at the
   motif scan: it should show a ✓ **HEXXH zinc-binding** match. Say: "matrix
   metalloproteinases are the textbook case for this motif — the two
   histidines coordinate the catalytic zinc ion, and the highlighted
   residues in the sequence view below are exactly that pattern."
3. Scroll to database enrichment on either example and point out that KEGG
   pathways come from a precomputed file, not a live call — "KEGG times out
   on this network, so it's fetched once during the build and cached."

---

## 6. What NOT to claim

- Do **not** say this beats homology-based annotation tools — it doesn't,
  and it isn't trying to (ECRECer reports ~93% on this exact task using
  sequence similarity; this project deliberately uses none).
- Do **not** say the ensemble is better than Extra Trees.
- Do **not** say the classifier gives definitive biological annotation.
- Do **not** say a motif match proves a protein is an enzyme — the motif
  scan is explicitly supplementary and never overrides the model.
- Do **not** say AlphaFold structures were predicted here — they are
  retrieved, precomputed, from AlphaFold DB.
- Do **not** say the KEGG false-positive test found "no enrichment" — it
  found the test underpowered (INCONCLUSIVE), which is a different claim.
- Do **not** claim novelty or patentability (extensive prior art; Indian
  Patents Act s.3(k)).

Correct framing, verbatim:

> "This project evaluates multiple machine-learning approaches for
> enzyme/non-enzyme classification using sequence-derived physicochemical
> features, combined with database-informed labeling and supplementary
> biological interpretation."

---

## 7. Limitations to volunteer

1. Homology-aware ROC-AUC (0.8347) is well below homology-based tools
   (~93%) — expected, since no sequence-similarity information is used.
2. The KEGG false-positive audit is underpowered (1 supported case) and
   reported as inconclusive, not negative.
3. The serine-protease motif is a 4-residue placeholder, not the official
   PROSITE pattern, and matches most proteins by chance.
4. Human-only scope; results may not generalise to other organisms.
5. Global amino-acid composition discards all positional/structural
   information.
6. MLP ranking third of four is an expected outcome on tabular data this
   size, not evidence against neural approaches in general.

---

## 8. Future work

- **ESM-2 protein-language-model embeddings** as a possible fifth comparison
  arm — likely to add signal, at the cost of interpretability (declined for
  this project for exactly that trade-off).
- **More organisms with genuine cross-organism testing** — train on one
  species, evaluate on another, to see whether physicochemical signal
  transfers or whether the model is quietly learning organism-specific
  composition.
- **Official PROSITE patterns / ScanProsite** in place of the simplified
  serine-protease regex.
- **Checking how published homology-based tools (e.g. ECRECer) define their
  negative class** — a fairer like-for-like comparison than quoting their
  headline accuracy against this project's very different evaluation setup.

---

## 9. Anticipated questions

**Why Extra Trees and not Random Forest?**
Extra Trees scored marginally higher on cross-validated ROC-AUC under both
splits (0.8603 vs 0.8543 homology-aware CV) and the selection rule picks the
CV leader. The extra randomness at split selection (random thresholds, not
just random features) tends to reduce variance further on data this size.

**Is train AUC 1.0 overfitting?**
It shows the trees are fully grown and memorise their training rows — that's
expected for unpruned Random Forest / Extra Trees, not by itself evidence of
a generalisation problem, since generalisation is judged on the held-out
homology-aware test set and cross-validation, not on train AUC. The learning
curve (CV ROC-AUC still rising, last-quarter gain only +0.0042) says the
bottleneck is feature expressiveness, not that the model has stopped
learning usefully.

**Why reject the ensemble that scored higher on test?**
Covered in §4 above — selection happens on cross-validation before the test
set is touched; using the test-set ranking to override that would be
circular.

**What is homology leakage and how was it measured?**
Paralogs and family members share near-identical amino-acid composition. A
random train/test split can put close relatives on both sides, so a model
can score well by recognising a family it has already seen rather than
learning real enzyme-vs-non-enzyme signal. Measured by clustering all 10,782
proteins at 40% identity / 80% coverage with MMseqs2 (8,022 clusters) and
comparing the same models' test ROC-AUC under a random split vs. a split
that keeps every cluster entirely on one side — the gap (up to 0.042 for
Extra Trees) is the leakage.

**Is it just protein size?**
No — the length/molecular-weight-only baseline reaches ROC-AUC 0.6451
(homology-aware), well above chance but far below the full model's 0.8347.
Size correlates with function but doesn't explain most of what the model
uses.

**Why did the MLP come third?**
Neural networks generally need more data to out-perform tree ensembles on
tabular (non-image, non-sequence, non-text) data of this size; this is a
well-known pattern in the ML literature, not a project-specific failure.

**Is 10,782 proteins enough?**
The learning curve shows CV ROC-AUC is still rising slightly at full size
(last-quarter gain +0.0042), so more data would likely help marginally — but
the curve is flattening, and train AUC is already 1.0, suggesting the
current feature set, not sample size, is closer to the real bottleneck.

**Are EC and GO independent?**
No — 99.76% of EC proteins also carry a catalytic GO term (the `ec2go`
mapping feeds EC evidence into GO automatically). The claim made is strictly
better coverage than EC alone (890 additional GO-only proteins), not
independent confirmation.

**Why does KEGG not support GO-only proteins?**
KEGG assigns EC numbers through orthology to characterised reactions — the
same *kind* of evidence UniProt EC uses, just propagated across species. A
protein with no EC-level evidence in UniProt usually has none in KEGG
either, by construction. Low KEGG support for GO-only proteins is therefore
expected, not evidence against them.

**What is the PSMA3 example?**
P25788 (PSMA3), a non-catalytic 20S proteasome alpha subunit, is correctly
labelled non-enzyme by UniProt but receives complex-level EC 3.4.25.1 from
KEGG orthology (the proteolytic activity belongs to different subunits of
the same complex). It's a concrete case of KEGG agreement being consistent
with, not proof of, correct labelling.

**Are the model's false positives hidden enzymes?**
Can't tell — only 1 of 261 false positives (and 0 of 686 true negatives)
carry any KEGG EC number at all, so the test has almost no statistical power
either way. Reported honestly as INCONCLUSIVE rather than "no enrichment".

**Why is AlphaFold not a model feature?**
AlphaFold structures only exist for proteins already characterised well
enough to be in UniProt — using that as a training feature would be
circular (the model would partly be learning "is this protein well-studied"
rather than "is this an enzyme"). It's used only for a separate, offline
disorder analysis.

**Did you predict 3D structures?**
No — AlphaFold DB precomputed structures are retrieved, never predicted
here.

**Why not RDKit?**
RDKit is a small-molecule cheminformatics toolkit; this project classifies
whole protein sequences, not small molecules, so it isn't the right tool.

**Why not deep learning / ESM-2 embeddings?**
Out of scope for this project's contribution (labelling strategy + honest
evaluation of interpretable models), and would cost interpretability.
Flagged explicitly as future work (§8).

**Is it novel or patentable?**
No. No novel algorithm is introduced, there is extensive prior art in
enzyme/non-enzyme classification (including homology-based tools that score
higher on this exact task), and under the Indian Patents Act s.3(k) this
kind of software/algorithm work is not patentable subject matter as
presented.

**What does the motif scan mean?**
It's a supplementary, rule-based check — three short regex patterns for
known catalytic motifs — reported alongside the ML prediction but never
overriding it. `training/motif_stats.py` measures how informative each
pattern actually is on this dataset: two of the three (serine-protease,
HEXXH) appear at similar rates in both classes here and carry little class
information; Walker A / P-loop is meaningfully enriched in enzymes (ratio
3.867).

**Why human only?**
Annotation depth varies enormously across species; mixing organisms risks
the model learning "which organism" instead of "is this an enzyme" (see
README §2/§14, and future work §8 for cross-organism testing).
