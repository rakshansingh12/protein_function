Superseded for labelling claims by docs/REVIEW2_VIVA_NOTES.md (GO-only wording).

# Review 1 — Viva Preparation Notes

Everything below is what you should be able to say without reading from a screen.

---

## 1. The one-sentence pitch

> "I predict whether a protein is an enzyme or a non-enzyme from its amino acid
> sequence alone, and the database contribution is that I define the label using
> two independent UniProt annotation sources instead of one."

If the examiner only remembers one thing, it should be **two sources, not one**.

---

## 2. The problem with the original approach

The first version of this project used a single rule:

```
EC number present  ->  enzyme
EC number absent   ->  non-enzyme
```

The second half of that rule is wrong. An EC number is an *assigned* annotation.
A protein can be a genuine, experimentally confirmed enzyme and still have no EC
number, because:

- EC classification is curated by hand and lags behind discovery
- some catalytic activities do not map cleanly onto the four-level EC hierarchy
- newly characterised or poorly studied proteins simply have not been assigned yet

So "no EC number" means **"not annotated with an EC number"**, not **"not an
enzyme"**. Training a classifier on that rule teaches it to reproduce annotation
gaps, not biology. Those mislabelled enzymes sit in the negative class and
actively push the decision boundary in the wrong direction.

**Say this out loud in the review. This is the marks-bearing insight.**

---

## 3. The consensus labelling rule

Two independent evidence sources from UniProt:

| Source | What it is |
|---|---|
| EC number | Enzyme Commission classification of a catalysed reaction |
| GO:0003824 | Gene Ontology molecular-function term "catalytic activity" |

```
ENZYME      if  (EC present)  OR  (GO:0003824 present)
NON-ENZYME  if  (EC absent)  AND  (GO:0003824 absent)
```

The positive rule is a **union**, so a protein only needs one source to speak up.
The negative rule is an **intersection**, so a protein is only called a
non-enzyme when both sources are silent. That asymmetry is the whole point: it
makes the negative class much harder to earn.

Every protein is tagged `EC_only`, `GO_only`, `EC_and_GO`, or `neither`, and the
pipeline prints the counts.

**The number to quote: the `GO_only` count.** That is exactly how many proteins
the old EC-only scheme would have mislabelled. It is a measured quantity, not a
claim.

---

## 4. The technical detail that will impress them

> "GO:0003824 is the *root* catalytic-activity term. UniProt entries are almost
> never annotated with the root — they carry specific descendants like GO:0004252
> serine-type endopeptidase activity or GO:0016301 kinase activity. So if I had
> just searched each entry's GO list for the literal string GO:0003824, I would
> have matched almost nothing and my labels would have been silently broken.
> Instead I resolve it with a UniProt *query*, `go:0003824`, because the UniProt
> search index expands the GO hierarchy and returns every descendant."

This is in `download_data.py` as a comment block. It shows you understand that
GO is a directed acyclic graph, not a flat list of tags.

---

## 5. Why three queries and set arithmetic

```python
EC  = accessions matching  ec:*
GO  = accessions matching  go:0003824
NEG = accessions matching  NOT ec:* AND NOT go:0003824

enzymes     = EC | GO
EC-only     = EC - GO
GO-only     = GO - EC
both        = EC & GO
non-enzymes = NEG
```

Three queries, then pure set logic. Nothing is inferred or guessed — every
category is defined by an explicit query you can paste into the UniProt website
and reproduce.

---

## 6. Dataset scoping decisions (expect to be challenged on these)

**Why Swiss-Prot / reviewed only?**
TrEMBL is machine-annotated. There, a missing annotation almost always means
"nobody has curated this yet". Restricting to manually reviewed entries is what
makes *absence* of an annotation informative. This directly supports the
negative class.

**Why one organism (human, 9606)?**
Annotation depth varies enormously across species. If I mixed a deeply curated
organism with a shallowly curated one, the negative class would be dominated by
the under-annotated species and the model could learn "which organism is this"
instead of "is this an enzyme". One organism keeps annotation quality uniform.

**Why `fragment:false`?**
Composition of a fragment is not representative of the whole protein.

**Why balance the classes?**
So accuracy stays interpretable and the models cannot win by predicting the
majority class. I downsample rather than upsample, because duplicating rows
would put near-identical proteins on both sides of the train/test split.

**Why deduplicate sequences and not just accessions?**
Isoforms and redundant entries can share an identical sequence under different
accessions. If one copy lands in train and another in test, the reported score is
inflated. That is data leakage and it is the classic way to accidentally report
99% accuracy.

---

## 7. The sanity check

I separately query documented non-catalytic families — transport proteins
(keyword KW-0813), structural molecule activity (GO:0005198), and
immunoglobulins — and measure how many of them land inside my negative set.

Important framing: **these are not used as labels.** They are an independent
audit. High overlap is evidence that "no EC and no catalytic GO" is capturing
genuinely non-catalytic proteins rather than under-annotated enzymes.

---

## 8. The 29 features

**20** amino acid composition (fraction of each standard residue, alphabetical
A..Y) **+ 9** global descriptors:

| Feature | Biological reason it might separate the classes |
|---|---|
| Sequence length | Catalysis needs a folded domain, which sets a size floor |
| Molecular weight | Correlates with length but weights residue identity |
| Aromaticity | Aromatic residues are common in substrate-binding pockets |
| Instability index | Dipeptide-based in-vitro stability estimate (Guruprasad) |
| Isoelectric point | Catalytic sites depend on charged residues, shifting net charge |
| GRAVY | Hydropathy separates soluble globular enzymes from membrane/structural proteins |
| Helix / turn / sheet fraction | Coarse secondary-structure profile from residue propensities |

The composition block is not filler — enzymes are enriched in catalytic residues
(His, Cys, Asp, Glu, Ser), so raw composition already carries functional signal.

**Worked example you can quote:** human carbonic anhydrase 2 (P00918), a zinc
metalloenzyme, comes out at **5.97% histidine**. The population average is around
2%. Three histidines coordinate the catalytic zinc ion. So the composition
features are picking up something chemically real.

---

## 9. Train/inference consistency — the architecture answer

There is exactly **one** feature implementation:
`backend/app/ml/feature_engineering.py`.

`training/feature_engineering.py` imports it. It contains no feature maths at
all. If the code were duplicated, editing one copy would produce a model whose
inputs no longer mean what it was trained on — and nothing would crash, the
predictions would just quietly become wrong.

**Also worth mentioning:** I compute amino acid composition from raw residue
counts rather than calling BioPython's percentage helper, because BioPython
renamed that helper *and* changed its scale from fractions to percentages
between releases. Doing the division myself means feature values are identical
on every BioPython version, so a model trained on one machine stays valid on
another. I found this while testing — the newer API returned 5.4 where the older
one returned 0.054.

---

## 10. Anticipated questions

**"Isn't GO:0003824 partly derived from EC? Are the sources really independent?"**
Good challenge, and the honest answer is that they are *not fully* independent —
some GO catalytic annotations are electronically inferred from EC mappings. But
they are independent enough to help: the `GO_only` count is non-zero, and every
one of those proteins is a case where GO had catalytic evidence and EC did not.
The union strictly increases recall of true enzymes over EC alone. I am not
claiming perfect independence; I am claiming strictly better coverage.

**"How do you know your negatives are actually non-enzymes?"**
I do not know with certainty, and I will not claim to. Requiring both sources to
be silent, restricting to manually reviewed entries, and the non-catalytic
family sanity check together make it far more defensible than EC alone. Residual
label noise is a stated limitation.

**"Why not use BLAST or sequence alignment?"**
Different problem. Alignment answers "what is this similar to". I am asking
whether global physicochemical properties alone carry enough signal to classify
function — no homology, no alignment. It is a cheaper and more general question.

**"Why not a deep learning model / protein language model?"**
Out of scope and unjustified at this dataset size. The project's contribution is
the labelling strategy and a fair comparison of interpretable models, not a novel
architecture. I would rather defend a model I can explain.

**"What if the model is just learning sequence length?"**
That is checkable and I will check it in Review 2 via feature importances and by
comparing against a length-only baseline.

---

## 11. What NOT to claim

- Do **not** say this creates a novel ML algorithm.
- Do **not** say the classifier provides definitive biological annotation.
- Do **not** say motif matching proves something is an enzyme (Review 2 topic).
- Do **not** pre-announce that Random Forest will win. The entire point of
  Review 2 is that the winner is *measured*, not assumed.

Correct framing:

> "This project evaluates multiple machine-learning approaches for
> enzyme/non-enzyme classification using sequence-derived physicochemical
> features, combined with database-informed labelling and supplementary
> biological interpretation."

---

## 12. Live demo script (2 minutes)

```bash
python training/download_data.py        # show the three UniProt queries scroll past
python training/data_preprocessing.py   # stop on the CONSENSUS LABELING REPORT block
python training/feature_engineering.py  # show 29 features + class means table
```

Pause on the labelling report and read out the `GO-only` line. Then say:

> "That number is how many proteins my previous version got wrong."

---

## 13. Honest limitations to volunteer

Volunteering limitations reads as confidence, not weakness.

1. EC and GO are not fully independent sources.
2. Human-only means results may not generalise to other organisms.
3. Global composition discards all positional and structural information.
4. Some residual label noise certainly remains in the negative class.
5. Balancing by downsampling discards real data.
