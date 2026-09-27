# HANDOFF PLAN — finish the project end to end

Read `CLAUDE.md` first; its rules override anything here. Work through the
phases in order. After finishing a phase: run its acceptance checks, append to
`docs/RESULTS_LOG.md` where stated, tick its checkbox below with a one-line
note, and make a local git commit. Then continue straight to the next phase
without waiting for me, unless a STOP condition occurs.

## Progress

- [x] Phase 0 — Preflight and git baseline — done; all packages already installed, artefacts verified, git initialized, baseline committed (`7c2fa39`)
- [ ] Phase 1 — KEGG script correction and GO-only characterisation
- [ ] Phase 2 — AlphaFold pLDDT analysis (analysis only)
- [ ] Phase 3 — Helper artefacts (sequence index, KEGG pathways, motif stats)
- [ ] Phase 4 — FastAPI backend
- [ ] Phase 5 — Frontend (exactly 3 files)
- [ ] Phase 6 — Tests, API docs, end-to-end check
- [ ] Phase 7 — README, Review 2 viva notes, Review 2 Gamma prompt
- [ ] Phase 8 — Final report

## Resume protocol

If a session ends early, a new session resumes from the first unchecked phase.
Before resuming, run `git log --oneline | head` and `git status` to see what was
done. If a phase is partly done, finish it rather than restarting it; never
redo network downloads that are already cached.

## Global STOP conditions (stop, explain, ask)

- Any artefact listed in CLAUDE.md is missing or fails to load.
- A step would require re-running a FINAL script or editing a forbidden file.
- A numeric result differs from a value this plan says must be unchanged.
- More than 10% of network requests in a batch fail with non-404 errors.
- A required package cannot be installed, or installing it would change the
  installed scikit-learn, numpy or pandas version.
- Anything else these instructions do not cover.

## RESULTS_LOG conventions

Append new sections with the next free section number. Paste command output
verbatim (minus ResourceTracker noise). Where a section asks for an
interpretation, apply the stated decision rule exactly and quote the numbers
the rule used. Never edit existing sections.

---

## Phase 0 — Preflight and git baseline

1. Environment record:
   ```bash
   .venv/bin/python -c "import sys, sklearn, numpy, pandas, Bio, scipy, requests; print(sys.version); print('sklearn', sklearn.__version__, 'numpy', numpy.__version__, 'pandas', pandas.__version__, 'biopython', Bio.__version__, 'scipy', scipy.__version__, 'requests', requests.__version__)" | tee logs/environment.txt
   ```
2. Install only missing web/test packages (check first with `.venv/bin/pip show`):
   `fastapi`, `uvicorn[standard]`, `pydantic`, `pytest`, `httpx`. Afterwards
   re-run step 1 into `logs/environment_after.txt` and confirm the sklearn,
   numpy and pandas versions did not change. If they changed: STOP.
3. Confirm every artefact listed in CLAUDE.md exists. Load
   `models/final_model.joblib` and call `predict_proba` on the features of the
   first row of `data/processed/features.csv`. If anything fails: STOP.
4. Git:
   - If not a repository (`git rev-parse --is-inside-work-tree` fails):
     `git init`.
   - Ensure `.gitignore` contains these lines (append any missing):
     `.venv/`, `__pycache__/`, `.pytest_cache/`, `data/raw/`,
     `data/processed/*.csv`, `models/*.joblib`, `models/kegg_pathways.json`,
     `models/sequence_index.json`, `.DS_Store`.
   - `git add -A`, then `git status --short` and confirm nothing under
     `data/raw/`, no `.joblib`, and no `.venv/` is staged.
   - Commit: `baseline before handoff`.

## Phase 1 — KEGG script correction and GO-only characterisation

Idempotency: if `training/validate_kegg.py` already contains `INCONCLUSIVE`
and `docs/RESULTS_LOG.md` already has a "GO-only composition" section, this
phase was done by Task 02: tick it and move on.

1. Back up: `cp training/validate_kegg.py logs/backup/validate_kegg.py.handoff.bak`
   and the same for `training/config.py` (`mkdir -p logs/backup` first).
2. In `training/config.py`, directly after the line
   `MIN_EXPECTED_PATHWAY_GENES = 3000`, add:
   ```python
   # The false-positive test is only meaningful if enough labelled non-enzymes in
   # the test set carry KEGG EC numbers for enrichment to be detectable.
   MIN_KEGG_SUPPORTED_FOR_TEST = 10
   ```
3. In `training/validate_kegg.py`, function `false_positive_audit`, replace the
   entire `if p_value < 0.05 and odds_ratio > 1: ... else: ...` block that
   prints the interpretation with:
   ```python
       # A test can only find enrichment if there is something to find. If almost
       # no negatives carry KEGG EC at all, "not significant" means "untestable",
       # not "the false positives are ordinary errors".
       total_supported = fp_hits + tn_hits
       if total_supported < config.MIN_KEGG_SUPPORTED_FOR_TEST:
           print(f"\nInterpretation: INCONCLUSIVE. Only {total_supported} labelled "
                 f"non-enzyme(s) in the test")
           print("set carry any KEGG EC number, so this test has almost no power to")
           print("detect enrichment either way. KEGG's EC assignments track the same")
           print("kind of reaction-level evidence as UniProt EC, so a protein missing")
           print("an EC number in UniProt usually lacks one in KEGG too. KEGG cannot")
           print("tell us whether these false positives are hidden enzymes.")
       elif p_value < 0.05 and odds_ratio > 1:
           print("\nInterpretation: KEGG enzyme evidence is significantly more")
           print("common among the model's false positives. Part of the apparent")
           print("error rate may be label noise: the model is flagging proteins that")
           print("an independent database also considers enzymes.")
       else:
           print("\nInterpretation: no significant enrichment despite adequate KEGG")
           print("coverage. The false positives look like ordinary model errors.")
   ```
4. In function `label_agreement`, directly before the line
   `    # Metabolic pathway membership, descriptive only.`, insert:
   ```python
       print("  Note: KEGG assigns EC numbers through orthology to characterised")
       print("  reactions, the same kind of evidence behind UniProt EC. Low KEGG")
       print("  support for GO-only proteins is therefore expected by construction,")
       print("  and does not by itself show that they are not enzymes.")
   ```
5. In the module docstring, replace the sentence claiming KEGG orthology is "a
   different evidence route ... so it is a meaningful cross-check" with:
   "This checks the EC-backed labels across species, but it rests on the same
   reaction-level evidence as UniProt EC, so it cannot independently confirm
   GO-only enzymes."
6. Syntax check both files with `ast.parse`. Run:
   ```bash
   .venv/bin/python training/validate_kegg.py 2>&1 | tee logs/validate_kegg_v2.log
   ```
   Acceptance: all three downloads report `cached`; Question 2 ends with
   `Interpretation: INCONCLUSIVE`; every numeric line matches
   `logs/validate_kegg.log` (compare lines containing digits, ignoring the new
   explanatory text). Any numeric difference: STOP.
7. GO-only characterisation. Run exactly (do not change the patterns):
   ```bash
   .venv/bin/python - << 'EOF' 2>&1 | tee logs/go_only_breakdown.log
   import pandas as pd
   df = pd.read_csv("data/processed/proteins_labeled.csv")
   go_only = df[df["evidence_class"] == "GO_only"].copy()
   names = go_only["protein_name"].fillna("")
   groups = {
       "ATPase / ABC":          r"atpase|atp-binding cassette|abc transporter",
       "GTPase / Ras / Rab":    r"gtpase|ras-related|\brab\b|\bras\b|guanine nucleotide-binding",
       "Transporter / channel": r"transporter|channel|solute carrier|exchanger",
       "Helicase":              r"helicase",
       "Kinase":                r"kinase",
       "Ubiquitin / ligase":    r"ubiquitin|ligase|ring finger",
       "Name ends in -ase":     r"ase\b",
   }
   print(f"GO-only proteins: {len(go_only)}\n")
   print("Keyword groups (overlapping; will not sum to the total):")
   for label, pattern in groups.items():
       hits = names.str.contains(pattern, case=False, regex=True)
       go_only[label] = hits
       print(f"  {label:<24}{int(hits.sum()):>5}  ({hits.mean():.1%})")
   none = ~go_only[list(groups)].any(axis=1)
   print(f"  {'Matches no group':<24}{int(none.sum()):>5}  ({none.mean():.1%})")
   switch_like = go_only[["ATPase / ABC", "GTPase / Ras / Rab", "Transporter / channel"]].any(axis=1)
   print(f"\nATPase OR GTPase OR transporter: {int(switch_like.sum())} ({switch_like.mean():.1%})")
   print("\nRandom sample of 25 names (seed 42):")
   for name in names.sample(25, random_state=42):
       print("  ", name)
   print("\nRandom sample of 15 names matching NO group (seed 42):")
   for name in go_only.loc[none, "protein_name"].fillna("").sample(min(15, int(none.sum())), random_state=42):
       print("  ", name)
   out = go_only[["accession", "protein_name"]].copy()
   out["length"] = go_only["sequence"].str.len()
   out.to_csv("data/processed/go_only_proteins.csv", index=False)
   print("\nSaved -> data/processed/go_only_proteins.csv")
   EOF
   ```
8. RESULTS_LOG: append "KEGG validation (corrected interpretation)" with the
   step 6 output, and "GO-only composition" with the step 7 output, then an
   interpretation paragraph using this decision rule on the
   "ATPase OR GTPase OR transporter" share:
   - >= 30%: "A substantial share of GO-only proteins are catalytic by GO's
     formal definition (ATP/GTP hydrolysis, transport-coupled activity) rather
     than classical enzymes. The GO-only group mixes classical enzymes and
     boundary cases."
   - < 30%: "Most GO-only proteins do not fall into the ATPase/GTPase/
     transporter boundary categories; by name, the group is dominated by other
     catalytic or uncharacterised proteins."
   Quote the share. Add one sentence on the "Matches no group" share.
9. Commit: `phase 1: KEGG interpretation fix, GO-only characterisation`.

## Phase 2 — AlphaFold pLDDT analysis (analysis only)

Purpose: test whether non-enzymes are more disordered than enzymes, which
would explain their higher instability index. This is NOT a model feature.

1. Add NEW constants to `training/config.py` (append at the end):
   `ALPHAFOLD_API_URL = "https://alphafold.ebi.ac.uk/api/prediction"`,
   `ALPHAFOLD_CACHE_DIR = RAW_DIR / "alphafold"`,
   `ALPHAFOLD_SAMPLE_PER_GROUP = 1000`,
   `ALPHAFOLD_REPORT_JSON = PROCESSED_DIR / "alphafold_analysis.json"`.
2. Probe one entry first: fetch `.../prediction/P04637`, print the top-level
   type and the keys of the first element. Confirm `entryId`,
   `globalMetricValue` (mean pLDDT) and `fractionPlddtVeryLow` (fraction of
   residues with pLDDT < 50) exist. If not: STOP.
3. Write `training/alphafold_analysis.py` (functions, comments, viva-readable):
   - Groups from `proteins_labeled.csv`: `GO_only` = all GO-only proteins;
     `EC_backed` = random 1,000 of evidence_class EC_and_GO or EC_only;
     `non_enzyme` = random 1,000 of label 0. Seed 42.
   - For each accession: if `ALPHAFOLD_CACHE_DIR/<acc>.json` exists, use it.
     Otherwise GET `<ALPHAFOLD_API_URL>/<acc>` with timeout (10, 30), up to 2
     retries, `time.sleep(0.1)` between requests. Cache the JSON list on
     success; on HTTP 404 cache `{"missing": true}`. Never cache other errors.
     Print progress every 100 proteins.
   - From the response, use the entry whose `entryId` ends with `-F1`, else the
     first entry. Record `mean_plddt = globalMetricValue` and
     `frac_very_low = fractionPlddtVeryLow`.
   - Join `instability_index` from `data/processed/features.csv`.
   - Report per group: n requested, n with AlphaFold data, n missing, median and
     IQR of mean_plddt and frac_very_low.
   - Mann-Whitney U (scipy, two-sided) for EC_backed vs non_enzyme, GO_only vs
     EC_backed, GO_only vs non_enzyme, on both metrics. Also report the
     probability of superiority `U / (n1 * n2)`, explained in a comment as "the
     chance a random protein from group A scores higher than one from group B".
   - Spearman correlation between instability_index and frac_very_low over all
     sampled proteins with data.
   - Save everything to `ALPHAFOLD_REPORT_JSON` and print a readable summary.
4. Run it: `.venv/bin/python training/alphafold_analysis.py 2>&1 | tee logs/alphafold_analysis.log`.
   If the non-404 failure rate exceeds 10%: STOP (cached results are kept).
5. RESULTS_LOG: append "AlphaFold pLDDT analysis" with the summary output and
   these decision rules, stated with the numbers they used:
   - H1 (enzymes are more ordered): SUPPORTED if EC_backed vs non_enzyme has
     p < 0.01 AND probability of superiority >= 0.60 for mean_plddt (EC_backed
     higher) AND frac_very_low is lower in EC_backed with p < 0.01. Otherwise
     NOT SUPPORTED.
   - H2 (instability index tracks predicted disorder): SUPPORTED if Spearman
     rho > 0.10 with p < 0.01. Otherwise NOT SUPPORTED.
   - GO-only placement: describe where GO_only medians sit relative to the other
     two groups, factually.
   - Caveat line: "pLDDT is AlphaFold's prediction confidence, a proxy for
     disorder, not a direct measurement of it."
6. Commit: `phase 2: AlphaFold pLDDT analysis`.

## Phase 3 — Helper artefacts

Write these small scripts in `training/`, run each, log output to `logs/`.

### 3a. `training/build_sequence_index.py` -> `models/sequence_index.json`
From `data/raw/uniprot_raw_combined.csv` (all 20,430 proteins): key =
SHA-256 hex of `clean_sequence(sequence)` (import from the canonical feature
module); value = `{accession, protein_name, label, evidence_class}`. Used by
the backend to recognise exact matches to known proteins. Print the count and
the number of duplicate-sequence collisions (keep the first).

### 3b. KEGG pathway names and `models/kegg_pathways.json`
1. Fetch names with curl, max 3 attempts, 60 s apart:
   `curl -4 --max-time 600 -o data/raw/kegg_hsa_pathway_names.tsv https://rest.kegg.jp/list/pathway/hsa`
   Valid lines look like `hsa00010<TAB>Glycolysis / Gluconeogenesis - Homo
   sapiens (human)` (the id may carry a `path:` prefix). If it fails 3 times:
   STOP.
2. `training/build_kegg_pathways.py`: combine `data/raw/uniprot_kegg_xref.tsv`,
   `kegg_hsa_enzyme.tsv`, `kegg_hsa_pathway.tsv` and the names file into
   `{accession: {"kegg_genes": [...], "ec": [...], "pathways": [{"id", "name"}]}}`
   for every accession in the sequence index. Strip the " - Homo sapiens
   (human)" suffix from names. Reuse parsing helpers from `validate_kegg.py`
   by importing them rather than copying code.

### 3c. Motif service and `models/motif_stats.json`
1. Create `backend/app/services/motif_service.py` (spec in Phase 4, section
   "motif_service") now, because 3c depends on it.
2. `training/motif_stats.py`: for each motif, the percentage of enzymes and of
   non-enzymes in `proteins_labeled.csv` with at least one match, plus the ratio
   enzyme% / non-enzyme%. Import `scan_motifs` from the service (single source
   of truth, same principle as the features). Save `models/motif_stats.json`.
3. RESULTS_LOG: append "Motif match rates by class" with the output, then:
   "A motif found at similar rates in both classes carries little class
   information in this dataset." Name the motif(s) this applies to (ratio
   between 0.8 and 1.25).
4. Commit: `phase 3: sequence index, KEGG pathway map, motif statistics`.

## Phase 4 — FastAPI backend

Files (create): `backend/__init__.py` (empty), `backend/app/main.py`,
`backend/app/api/routes.py`, `backend/app/api/schemas.py`,
`backend/app/ml/model_loader.py`, `backend/app/services/prediction_service.py`,
`similarity_service.py`, `enrichment_service.py` (motif_service exists).

### model_loader (ml)
- Project root = `Path(__file__).resolve().parents[3]`.
- `load_artefacts()` loads, once (module-level cache): final_model, scaler,
  training_features, class_stats, model_results, metadata, and optionally
  model_results_random_split, sequence_index, kegg_pathways, motif_stats
  (optional ones may be missing -> None).
- Missing required artefacts raise a clear `ArtefactsMissingError` with the
  list of missing files. Routes turn it into HTTP 503.

### similarity_service
- Fit `NearestNeighbors(n_neighbors=5, metric="euclidean")` once on
  `features_scaled`. Query = `scaler.transform([features])`.
- Return accession, class ("enzyme"/"non-enzyme"), distance (float) and
  `similarity = 100 / (1 + distance)` rounded to 1 decimal. Comment why:
  a simple, monotonic, explainable 0-100 score; 100 means identical features.
- Comment that the search covers the training split only.

### motif_service
- `MOTIFS`: list of dicts with name, regex, notation, explanation, note:
  1. Serine protease-related (simplified): regex `[DES][ST].[LIVM]`, notation
     `[DES]-[ST]-x-[LIVM]`. Comment: simplified placeholder approximation.
     `# TODO: Replace this simplified pattern with the official PROSITE pattern
     before production use.` Note that official PROSITE patterns or ScanProsite
     should be preferred, and that this 4-residue pattern matches most proteins
     by chance (low specificity).
  2. HEXXH zinc-binding: regex `HE..H`, notation `H-E-x-x-H`. Explanation: a
     characteristic motif of zinc metalloproteases and other metalloenzymes; the
     two histidines coordinate the catalytic zinc.
  3. Walker A / P-loop: regex `[AG].{4}GK[ST]`, notation `[AG]-x(4)-G-K-[ST]`.
     Explanation: phosphate-binding loop in ATP/GTP-binding proteins.
- `scan_motifs(sequence)` -> `{"matches": [{name, start, end, match,
  explanation}], "not_found": [names], "disclaimer": DISCLAIMER}`. 1-based
  inclusive positions. Non-overlapping `re.finditer` (comment this choice).
- `DISCLAIMER = "Known catalytic motif scan — supplementary rule-based
  analysis. Motif detection does not override the machine-learning prediction."`

### enrichment_service (isolated; must never raise)
- Only for accessions present in `sequence_index`. Validate accession format
  with the UniProt regex
  `^([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})$`.
- UniProt: GET `https://rest.uniprot.org/uniprotkb/<acc>.json`, timeout (3, 8).
  Extract recommended protein name, organism scientific name, subcellular
  locations (comments with commentType "SUBCELLULAR LOCATION"), and PDB cross
  references (database "PDB": id plus Method/Resolution/Chains properties).
  Inspect one real response first and save a trimmed copy as
  `backend/tests/fixtures/uniprot_P00918.json` for offline tests.
- PDB: from the UniProt cross-references; link `https://www.rcsb.org/structure/<id>`.
- AlphaFold: GET the prediction API, timeout (3, 8); return entryId, mean
  pLDDT, fractionPlddtVeryLow, and link `https://alphafold.ebi.ac.uk/entry/<acc>`.
  Save a trimmed fixture `backend/tests/fixtures/alphafold_P00918.json`.
- KEGG: from `models/kegg_pathways.json` only (no live KEGG call; comment why:
  KEGG times out on this network and results are precomputed). Links
  `https://www.kegg.jp/entry/<gene>` and `https://www.kegg.jp/pathway/<id>`.
- Catch every exception per source (timeout, HTTP error, bad JSON, missing
  keys) and set that source to null. In-memory cache per accession. If every
  source is empty, include `"message": "No additional database records found."`

### prediction_service (thin orchestrator)
`predict(raw_sequence)`: `extract_from_raw` -> on failure raise ValueError with
the validation message -> `predict_proba` -> label with threshold 0.5 ->
similarity -> motifs (+ motif_stats per motif if available) -> comparison rows
for the 5 COMPARISON_PROPERTIES with input, enzyme mean/std, non-enzyme
mean/std (from class_stats) -> dataset match via SHA-256 lookup, with
`in_training_split` = accession in training_features["accessions"].

### routes and schemas (prefix `/api`)
- `GET /api/health` -> `{"status": "ok", "model_loaded": bool}`.
- `GET /api/model-info` -> final model name, split_mode, selection rule,
  ensemble_selected, training size and class counts, and per model: test
  roc_auc, f1, accuracy, precision, recall, plus random-split roc_auc when
  that file exists; also the size baseline (test roc_auc, lift).
- `POST /api/predict` body `{"sequence": str}` (max 20,000 characters) ->
  prediction ("ENZYME"/"NON-ENZYME"), probability_enzyme, confidence,
  model_name, sequence_length, cleaned_sequence, features (all 29),
  comparison, similar_proteins, motifs, dataset_match (or null), notes (list:
  the model was trained on human proteins; headline homology-aware ROC-AUC
  read from model_results.json; if dataset_match.in_training_split, that the
  model saw this protein during training so the result is not an independent
  test). Invalid sequence -> HTTP 400 with the validation message.
- `GET /api/enrich/{accession}` -> enrichment result; 400 for a malformed
  accession; 404 with a message if the accession is not in the dataset.
  External failures never produce a 5xx.
- `main.py`: create the app, include the router, load artefacts at startup
  (log a warning instead of crashing if missing), then mount
  `frontend/` at `/` with `StaticFiles(html=True)` AFTER the API router, so the
  UI and API share one origin.

Acceptance: `.venv/bin/python -c "from backend.app.main import app"` works from
the project root, and `.venv/bin/python training/validate_kegg.py` still runs
(proves the training imports still work; it uses cached files).
Commit: `phase 4: FastAPI backend`.

## Phase 5 — Frontend (exactly 3 files)

Design: white or light-grey background, ONE accent colour, system sans-serif
font stack, generous whitespace, simple cards, minimal borders, no gradients,
no heavy shadows, no dark mode. Clean academic research prototype.

Single page, sections in order:
1. Header: title, one-line description, and a short scope note ("Research
   prototype trained on reviewed human proteins. Not a definitive annotation
   tool.").
2. Input: textarea (FASTA allowed), Predict and Clear buttons, a button that
   loads an example sequence (take a real enzyme sequence from the dataset,
   e.g. P00918 if present, and embed it in script.js), client-side validation
   mirroring the backend (non-empty, >= 50 residues after stripping, standard
   residues), error area.
3. Prediction: ENZYME / NON-ENZYME, probability as %, final model name from
   the response. Dataset-match banner when applicable (accession linked to
   `https://www.uniprot.org/uniprotkb/<acc>/entry`, database label, and the
   training-split notice). Show the notes list.
4. Model performance: table from `/api/model-info` (Model, ROC-AUC, F1, and
   random-split ROC-AUC if present), final model row highlighted, caption
   explaining the homology-aware split and the size baseline value.
5. Similar proteins: table with Accession (linked), Class, Distance (3 dp),
   Similarity (%).
6. Physicochemical comparison: for each of the 5 properties a small table row
   (Input, Enzyme avg ± SD, Non-enzyme avg ± SD) plus three horizontal CSS bars
   scaled to the largest absolute value of the three; GRAVY can be negative, so
   draw bars from a centre line (left negative, right positive). Include a line
   on the instability index (values above 40 are conventionally "unstable").
7. Motif scan: disclaimer text verbatim; for each match "✓ name", position
   start–end, matched residues, explanation, and the class match rates from
   motif_stats; "No <name> motif detected." for the rest; the serine note about
   low specificity; the sequence in monospace, wrapped at 60 residues, with
   matched regions wrapped in `<span class="motif">` built in JS from positions
   (escape text; never inject server HTML).
8. Database enrichment (only with a dataset match): "Loading database
   records…", then UniProt (protein, organism, subcellular location), PDB
   (structure IDs linked, method, resolution), KEGG (pathways linked),
   AlphaFold (mean pLDDT, fraction pLDDT < 50, link "View predicted 3D
   structure at AlphaFold DB"). State that structures are retrieved from
   AlphaFold DB, not predicted here. If nothing: "No additional database
   records found." Without a dataset match, show one line explaining that
   enrichment runs only for sequences that exactly match a known UniProt entry,
   and that predicting structures for novel sequences is out of scope.
9. Footer: the framing sentence from the original brief: "This project
   evaluates multiple machine-learning approaches for enzyme/non-enzyme
   classification using sequence-derived physicochemical features, combined with
   database-informed labeling and supplementary biological interpretation."

JS: `fetch` relative URLs (`/api/...`); loading states; disable buttons while
busy; show backend error messages; no external libraries.
Commit: `phase 5: frontend`.

## Phase 6 — Tests, API docs, end-to-end check

1. `backend/tests/` with a `conftest.py` that puts the project root on
   `sys.path` and skips artefact-dependent tests when artefacts are missing.
   Tests (simple, readable):
   - `test_features.py`: 29 features; composition sums to 1; FASTA/newline
     cleaning; rejects short, empty, non-standard sequences.
   - `test_motifs.py`: synthetic sequences containing HEXXH and Walker A are
     found at correct 1-based positions; absent motifs listed in not_found.
   - `test_model_loader.py`: artefacts load; model has predict_proba.
   - `test_similarity.py`: 5 neighbours, sorted by distance, similarity in
     (0, 100].
   - `test_api.py` (FastAPI TestClient): health; model-info; predict on a real
     dataset sequence (200, fields present); invalid sequence -> 400; malformed
     accession -> 400; enrichment with network mocked to fail (monkeypatch
     `requests.get` to raise) -> 200 with nulls, never 5xx; enrichment parsing
     from the saved fixtures.
   Run `.venv/bin/python -m pytest backend/tests -q 2>&1 | tee logs/pytest.log`.
   All tests must pass. Fix code, not tests, unless a test is wrong about the
   spec.
2. `docs/API.md`: every endpoint, request/response examples taken from real
   responses, status codes, the similarity formula, enrichment behaviour.
3. End-to-end: start `.venv/bin/uvicorn backend.app.main:app --port 8000` in
   the background, wait for `/api/health`, then curl: health, model-info,
   predict with a real dataset sequence, predict with "HELLO", enrich for that
   sequence's accession, and `/` (must return the HTML). Save all to
   `logs/e2e_check.log`, stop the server. Append a short "End-to-end check"
   section to RESULTS_LOG (status codes and prediction fields, verbatim).
4. Commit: `phase 6: tests, API docs, end-to-end check`.

## Phase 7 — README, Review 2 viva notes, Review 2 Gamma prompt

Every number must come from `docs/RESULTS_LOG.md` or the JSON artefacts.
Follow the Mandatory framing in CLAUDE.md throughout.

1. `backend/requirements.txt`: pin each listed package to the version actually
   installed in `.venv` (read with `.venv/bin/pip show`); include scipy.
2. `README.md` (rewrite; short but complete): 1 purpose; 2 biological
   methodology (EC + GO consensus, GO hierarchy resolved by query, 99.76%
   overlap, GO-only wording); 3 the 29 features and their redundancy;
   4 ML methodology (four models, why each); 5 model selection (stratified CV,
   ROC-AUC then F1, select on CV, test once); 6 ensemble strategy (tested,
   rejected, why); 7 evaluation integrity (size baseline; homology-aware split
   with the random vs homology table); 8 KEGG validation and its limits
   (incl. PSMA3); 9 AlphaFold analysis (H1/H2 outcomes; analysis only);
   10 similar protein finder; 11 physicochemical comparison; 12 motif scanning
   (incl. motif_stats and placeholder note); 13 database enrichment;
   14 limitations; 15 how to run (install, full pipeline order incl.
   cluster_sequences, validate_kegg, alphafold_analysis and the 3 helper
   scripts, then `uvicorn backend.app.main:app --reload` and open
   http://127.0.0.1:8000/; `pytest`); 16 data licences (UniProt CC BY 4.0,
   AlphaFold DB CC BY 4.0, KEGG academic use only and not redistributed).
3. `docs/REVIEW2_VIVA_NOTES.md`, in the style of `docs/REVIEW1_VIVA_NOTES.md`:
   one-sentence pitch; what changed since Review 1; a numbers-to-memorise
   table; methodology explanations; a live demo script (start server, example
   sequence, what to point at; pick a dataset enzyme that contains HEXXH or
   Walker A and name its accession); what NOT to claim; limitations; future
   work (ESM-2 arm, more organisms with cross-organism testing, official
   PROSITE patterns, checking how published tools define negatives). Include
   anticipated questions with model answers for at least: why Extra Trees and
   not Random Forest; is train AUC 1.0 overfitting; why reject the ensemble that
   scored higher on test; what homology leakage is and how it was measured; is
   it just protein size; why the MLP came third; is 10,782 proteins enough;
   are EC and GO independent; why KEGG does not support GO-only; the PSMA3
   example; are the false positives hidden enzymes; why AlphaFold is not a
   model feature; did you predict 3D structures; why not RDKit; why not deep
   learning / ESM-2; is it novel or patentable; what the motif scan means; why
   human only.
4. Add one line at the top of `docs/REVIEW1_VIVA_NOTES.md`: "Superseded for
   labelling claims by docs/REVIEW2_VIVA_NOTES.md (GO-only wording)."
5. `docs/GAMMA_PROMPT_REVIEW2.md`, in the style of
   `docs/GAMMA_PROMPT_REVIEW1.md`: usage instructions (Presentation, ~16
   cards, Detailed text, light academic theme), then one fenced prompt
   describing each slide with the real numbers: title; recap of the labelling
   result (qualified GO-only wording); pipeline overview; model comparison
   table; model selection rule; ensemble decision; size baseline; homology
   leakage (clusters + random vs homology table); learning curve; confusion
   matrix; KEGG validation and its limits (PSMA3); GO-only composition;
   AlphaFold analysis; the web application (architecture + features);
   limitations; conclusions and future work. Tell Gamma not to invent any
   numbers. End with a post-generation checklist.
6. Commit: `phase 7: README, Review 2 viva notes, Review 2 Gamma prompt`.

## Phase 8 — Final report

1. Run the full test suite once more and `git status` (must be clean).
2. Write `docs/HANDOFF_SUMMARY.md`: what was built in each phase, key numbers
   (from RESULTS_LOG), H1/H2 outcomes, how to run the app, how to run tests,
   where the viva notes and Gamma prompt are, and any open issues.
3. Tick Phase 8, commit `phase 8: handoff summary`, print the summary in the
   terminal, and stop.
