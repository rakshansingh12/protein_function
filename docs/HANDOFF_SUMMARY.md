# Handoff Summary

Full history: `git log --oneline` (8 commits, `7c2fa39`..`264c584`, all local,
none pushed). Full numeric detail for every phase is in `docs/RESULTS_LOG.md`.

## What was built, by phase

**Phase 0 — Preflight and git baseline** (`7c2fa39`). Confirmed all required
packages (fastapi, uvicorn, pydantic, pytest, httpx) were already installed
with no version drift to sklearn/numpy/pandas; confirmed every artefact in
`CLAUDE.md` exists and the saved model loads and predicts; initialised git
(the directory was not previously a repository) and committed the pre-handoff
state.

**Phase 1 — KEGG interpretation fix, GO-only characterisation** (`0a97b1e`).
Added `MIN_KEGG_SUPPORTED_FOR_TEST = 10` to `training/config.py`.
`training/validate_kegg.py`'s false-positive audit now reports
**INCONCLUSIVE** (not "no enrichment") when too few negatives carry any KEGG
EC number to give the test power — only 1 of 261 test-set false positives do.
Added a GO-only characterisation script output: of 890 GO-only proteins, only
7.5% fall into ATPase/GTPase/transporter "boundary" categories; 65.3% match
none of the scanned keyword groups.

**Phase 2 — AlphaFold pLDDT analysis** (`74214f8`). New
`training/alphafold_analysis.py`: tests whether enzymes are structurally more
ordered than non-enzymes (analysis only, never a model feature). Over 2,890
proteins (0% fetch failures): **H1 SUPPORTED** (EC-backed proteins have
higher mean pLDDT than non-enzymes, p = 4.9e-87) and **H2 SUPPORTED**
(instability index correlates with predicted disorder, Spearman rho =
0.5347, p ≈ 0). GO-only proteins sit between EC-backed and non-enzyme on both
metrics.

**Phase 3 — Helper artefacts** (`fb11091`). Three new `training/` scripts:
`build_sequence_index.py` (SHA-256 sequence hash → known-protein lookup,
20,352 unique sequences, 78 collisions), `build_kegg_pathways.py`
(precomputed per-accession KEGG genes/EC/pathways, avoids a live KEGG call
from the backend), `motif_stats.py` (per-motif class match rates — Walker
A / P-loop is the one motif with real class signal here, ratio 3.867; the
other two are close to 1). Also added `backend/app/services/motif_service.py`.

**Phase 4 — FastAPI backend** (`35df39f`). `backend/app/ml/model_loader.py`,
and `backend/app/services/{similarity,enrichment,prediction}_service.py`,
`backend/app/api/{routes,schemas}.py`, `backend/app/main.py`. Manually
smoke-tested (health/model-info/predict/enrich, 200/400/404 all as
expected) before committing.

**Phase 5 — Frontend** (`aa27666`). Exactly `frontend/{index.html,style.css,
script.js}`, vanilla, no frameworks or CDNs. Visually verified in a real
browser: prediction flow, dataset-match banner, model performance table,
similar proteins, physicochemical comparison bars (including the
zero-centred GRAVY bar), motif scan with sequence highlighting, database
enrichment, and client-side validation — no console errors.

**Phase 6 — Tests, API docs, end-to-end check** (`5fc2179`). 23 pytest tests
across `test_features.py`, `test_motifs.py`, `test_model_loader.py`,
`test_similarity.py`, `test_api.py` — all passing. `docs/API.md` written
from real captured responses. End-to-end curl check against a live server:
6/6 expected status codes (health/model-info/predict/predict-invalid/enrich/
frontend root).

**Phase 7 — README, Review 2 viva notes, Review 2 Gamma prompt**
(`264c584`). `README.md` rewritten (16 sections per the handoff plan).
`docs/REVIEW2_VIVA_NOTES.md` and `docs/GAMMA_PROMPT_REVIEW2.md` written in
the style of the Review 1 versions; `docs/REVIEW1_VIVA_NOTES.md` marked
superseded for labelling claims. Also caught and fixed a stale dependency
pin: `backend/requirements.txt` said `scipy==1.14.1` but the `.venv` actually
has `scipy==1.18.1`.

**Phase 8 — Final report** (this commit). Full test suite re-run (23/23
passed), `git status` clean before this commit, this summary written.

## Key numbers

See `docs/RESULTS_LOG.md` for every number with its source. Headline: **Extra
Trees, homology-aware test ROC-AUC 0.8347** (random-split 0.8770 — the
difference is homology leakage, not a competing headline). Ensemble tested,
not adopted (CV gain +0.0012, below the +0.002 threshold). Size-only baseline
0.6451 (lift +0.1896). KEGG maps 95.2% of the dataset; the false-positive
enrichment test is INCONCLUSIVE (underpowered), not negative. AlphaFold H1
and H2 both SUPPORTED.

## How to run

```bash
uvicorn backend.app.main:app --reload
# open http://127.0.0.1:8000/

pytest backend/tests -q
```

Full pipeline order (already run for this dataset; see `README.md` §15 for
the complete list including the three Phase 3 helper scripts and
`alphafold_analysis.py`).

## Where things are

- Viva prep: `docs/REVIEW2_VIVA_NOTES.md` (one-sentence pitch, numbers to
  memorise, demo script using Q99542/matrix metalloproteinase-19 for the
  HEXXH motif, full anticipated-questions bank).
- Slide generation: `docs/GAMMA_PROMPT_REVIEW2.md` (16-slide prompt, all
  numbers pre-filled, plus a post-generation drift checklist).
- API reference: `docs/API.md`.
- Full numeric log, every phase: `docs/RESULTS_LOG.md`.

## Open issues / things worth knowing

1. **Files outside the original allowed-file list.** Running
   `training/validate_kegg.py` (Step 4 of the earlier `CLAUDE_CODE_TASK.md`
   session, before this handoff plan started) wrote
   `data/processed/kegg_validation.json` and
   `data/processed/kegg_candidate_mislabels.csv`, which were not on that
   session's allowed-file list. Flagged and confirmed with the user at the
   time; both files are legitimate script output and are now part of the git
   history from the Phase 0 baseline commit.
2. **FastAPI `on_event` deprecation warning.** `backend/app/main.py` uses
   `@app.on_event("startup")`, which current FastAPI flags as deprecated in
   favour of lifespan handlers. Tests pass and the app works correctly; this
   is a style modernisation, not a bug, and was left as-is since it wasn't
   part of any phase's acceptance criteria.
3. **Serine-protease motif is a known placeholder** (documented in the code,
   README, and viva notes) — a 4-residue regex, not the official PROSITE
   pattern, and matches most proteins by chance. Flagged as future work.
4. Nothing was pushed to any remote; all 8 commits are local only.
