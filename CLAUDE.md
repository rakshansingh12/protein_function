# CLAUDE.md — Protein Function Classifier (enzyme vs non-enzyme)

Course project for a Biological Databases subject. The student must understand,
explain and defend every part in a viva. Simplicity and honesty beat cleverness.

- Work plan: `docs/HANDOFF_PLAN.md` (phases with checkboxes; resume from the
  first unchecked phase).
- Results record: `docs/RESULTS_LOG.md` (append only).

## Hard rules

1. FINAL, NEVER RE-RUN: `training/download_data.py`, `data_preprocessing.py`,
   `feature_engineering.py`, `cluster_sequences.py`, `train.py`. Their outputs
   in `data/processed/` and `models/` are final. If a task seems to need a
   re-run, STOP and ask.
2. Never change labelling logic, the 29-feature extraction, existing thresholds
   or constants, random seeds (42), model settings, or existing files in
   `models/`. Adding NEW constants to `training/config.py` for NEW scripts is
   allowed.
3. Never delete files in `data/`, `models/`, `logs/`.
4. Never invent, estimate or round numbers. Every number written anywhere must
   be copied from a file or a command's output. If files disagree with the
   summary in this CLAUDE.md, the files win: STOP and report the discrepancy.
5. Python: always `.venv/bin/python` and `.venv/bin/pip`. Do NOT run
   `pip install -r backend/requirements.txt`: it could change scikit-learn and
   break the saved joblib models. Install only missing packages, unpinned.
   Allowed packages: fastapi, uvicorn[standard], pydantic, scikit-learn, joblib,
   numpy, pandas, biopython, requests, scipy, pytest, httpx. No torch,
   tensorflow, rdkit, or any other dependency.
6. Frontend = exactly 3 files: `frontend/index.html`, `style.css`, `script.js`.
   Vanilla HTML/CSS/JS. No frameworks, CDNs, chart or 3D libraries.
7. Git: commit locally at the end of each phase. Never push. Never commit
   `data/raw/`, KEGG-derived files, or `*.joblib` (enforced via .gitignore).
8. Network: UniProt, AlphaFold DB and KEGG are shared academic services. Cache
   every response on disk, keep requests sequential with small delays. KEGG is
   academic/non-commercial only; KEGG-derived files stay out of git. For KEGG,
   use `curl -4` (Python requests times out on this network).
9. `Exception ignored in: <function ResourceTracker.__del__` messages are
   harmless Python 3.12 cleanup noise. Ignore them; do not "fix" them.
10. When in doubt, STOP and ask. Never improvise a workaround that changes data
    sources, methods, or earlier results.

## Code style

- Functions over classes, meaningful names, comments that explain the biology
  or ML reason. No design patterns for their own sake. Readable in a viva.
- Backend layering: routes -> services (thin orchestration) -> ml (computation).
- Relative imports inside `backend/app`. The server runs from the project root
  with `uvicorn backend.app.main:app --reload`. `training/` scripts import
  `app.ml.feature_engineering` via `sys.path` and must keep working.
- Code must work with the pandas/numpy/scikit-learn versions already installed.

## Artefacts (read-only)

- `models/final_model.joblib`: sklearn Pipeline(StandardScaler, ExtraTrees).
  Takes RAW 29 features in `FEATURE_NAMES` order; has predict/predict_proba.
- `models/scaler.joblib`: StandardScaler fit on the training split. Used ONLY
  to put features in the similar-protein search space.
- `models/training_features.joblib`: dict with `accessions`, `labels`,
  `features_scaled` (n_train x 29), `feature_names`. Training split only.
- `models/class_stats.json`: `{"enzyme"|"non_enzyme": {<prop>: {"mean","std"},
  ..., "count"}}` for isoelectric_point, gravy, molecular_weight, aromaticity,
  instability_index. Training split only.
- `models/model_results.json`: `best_model`, `split_mode` ("homology_aware"),
  `models[<name>]["cross_validation"|"test"]` with accuracy, precision, recall,
  f1, roc_auc (test also has confusion_matrix), `size_baseline`
  {cv, test, lift_of_full_model}, `learning_curve`, `selection_rule`,
  `ensemble_selected`. `models/model_results_random_split.json`: same schema
  for the earlier random split (no split_mode key).
- `models/metadata.json`: feature_names, counts, selected_model, split_mode.
- Canonical features: `backend/app/ml/feature_engineering.py`
  (clean_sequence, validate_sequence, calculate_features, extract_from_raw,
  FEATURE_NAMES, COMPARISON_PROPERTIES).
- Data: `data/processed/proteins_labeled.csv` (balanced 10,782; columns incl.
  accession, protein_name, sequence, evidence_class, label),
  `data/raw/uniprot_raw_combined.csv` (all 20,430, pre-cleaning),
  `data/processed/features.csv`, `clusters.csv`, `test_predictions.csv`.
- Labels: 1 = enzyme, 0 = non_enzyme.

## Established findings (summary; files are the source of truth)

- Labelling, complete reviewed non-fragment human proteome (20,430): EC 4,613;
  GO:0003824 incl. descendants 5,540; EC-only 11; GO-only 938; both 4,602;
  neither 14,879. After cleaning (19,767): EC-only 11, GO-only 890, both 4,490,
  neither 14,376. Balanced to 10,782 (5,391 per class).
- 99.76% of EC proteins also carry catalytic GO (ec2go mapping, directional).
- Class means enzyme vs non-enzyme: MW 64,405 vs 52,404 Da; instability 45.43
  vs 50.76; pI 7.18 vs 7.43; GRAVY -0.300 vs -0.355; aromaticity 0.086 vs 0.077.
- MMseqs2 (40% identity, 80% coverage): 8,022 clusters; 38.4% of proteins in
  multi-member clusters; largest 141; 52 clusters contain both labels.
- Test ROC-AUC, random -> homology-aware split: Extra Trees 0.8770 -> 0.8347,
  Random Forest 0.8698 -> 0.8285, MLP 0.8556 -> 0.8205, Logistic Regression
  0.7468 -> 0.7305. Extra Trees selected under both. Best test ensemble
  (RF+ET+MLP, 0.8368) rejected because selection uses cross-validation.
- Size-only baseline (MW + length) 0.6451, lift +0.1896 (homology-aware).
- Learning curve CV 0.829 -> 0.860, last-quarter gain +0.0042; train AUC 1.0
  (fully grown trees memorise; bottleneck is features, not data).
- Homology-aware test confusion: TN 764, FP 270, FN 242, TP 814.
- KEGG: 95.2% mapped; enzymes with KEGG EC 63.3%; non-enzymes 0.3% (16);
  EC_and_GO 74.2%; EC_only 7/11; GO_only 50/838 (6.0%). False-positive test
  1/261 vs 0/686, p = 0.276: INCONCLUSIVE (underpowered). P25788 (PSMA3, a
  non-catalytic 20S proteasome alpha subunit) gets complex-level EC 3.4.25.1
  from KEGG while UniProt labels it non-enzyme.

## Mandatory framing (docs, UI, slides)

- A rigorous STUDY, not a competitive tool: homology-based tools do better
  (e.g. ECRECer reports ~93% accuracy on enzyme vs non-enzyme). No novel
  algorithm. Not patentable (extensive prior art; Indian Patents Act s.3(k)).
  Contribution = database-informed labelling + honest evaluation.
- Headline performance = homology-aware ROC-AUC 0.8347. Random-split 0.8770
  appears only to quantify homology leakage (~0.04, mostly in flexible models).
- GO-only wording: "890 proteins carry curated catalytic GO evidence but no EC
  number; the EC-only scheme would call them non-enzymes. KEGG cannot
  independently confirm them, because its EC assignments rest on the same
  reaction-level evidence." Never write "890 proteins were mislabelled" alone.
- EC and GO are NOT independent (99.76%): claim better coverage, not
  independence. KEGG results are consistent with the negative class, not proof.
- A large gap in class means is not separability (size baseline 0.645).
- The 29 features are not independent (aromaticity = F+W+Y; GRAVY and
  helix/turn/sheet are composition-weighted). Length, instability index and pI
  add the most beyond composition.
- MLP ranking third is expected on tabular data of this size; not a failure.
- AlphaFold is analysis only, never a model feature (circular: only available
  for proteins already in UniProt). We RETRIEVE precomputed structures; never
  claim we predicted 3D structures. pLDDT is prediction confidence, a proxy for
  disorder, not disorder itself.
- The motif scan is rule-based and never overrides the ML prediction. The
  serine-protease regex is a low-specificity placeholder (TODO: official
  PROSITE pattern / ScanProsite).
- RDKit declined (small-molecule cheminformatics tool). ESM-2 embeddings are
  future work (possible fifth comparison arm; costs interpretability).
- Never claim an ensemble is better, that the classifier gives definitive
  annotation, or that a motif proves enzymatic function.
