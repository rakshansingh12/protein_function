# Task: install updated KEGG validation files, fetch KEGG data, run validation, collect results

You are working in a bioinformatics course project that classifies proteins as
enzyme vs non-enzyme. The pipeline is already built and has already been run.
Your job is narrow: finish the KEGG validation step and gather results into one
report. Do exactly the steps below, in order. Do not improve, refactor, or
extend anything.

## Project context (read, do not change)

- Project root: the current working directory (`protein-function-classifier/`).
- Python environment: `.venv/` in the project root. Use `.venv/bin/python` for
  every Python command.
- Already completed and must NOT be re-run: `download_data.py`,
  `data_preprocessing.py`, `feature_engineering.py`, `cluster_sequences.py`,
  `train.py`. Their outputs in `data/processed/` and `models/` are final.
- `models/model_results.json` holds the current homology-aware training results.
  `models/model_results_random_split.json` holds the earlier random-split results.
- The KEGG REST API is for academic, non-commercial use. Be polite to it.

## Hard rules

1. The only files you may create or overwrite are:
   - `training/validate_kegg.py` and `training/config.py` (step 2 only)
   - `data/raw/kegg_hsa_enzyme.tsv` and `data/raw/kegg_hsa_pathway.tsv`
   - files inside a new `logs/` directory
   - `docs/RESULTS_LOG.md`
2. Do not edit any other file. Do not change labelling logic, feature code,
   thresholds, random seeds, or model settings.
3. Do not delete anything in `data/` or `models/`, except a KEGG `.tsv` file in
   `data/raw/` that you have confirmed is invalid (step 3).
4. Do not run `git commit` or `git push`.
5. Never invent, estimate, or round numbers. Copy values exactly as printed or
   stored. If a value is missing, write "not available".
6. Messages starting `Exception ignored in: <function ResourceTracker.__del__`
   are a known harmless Python 3.12 multiprocessing cleanup message. Ignore
   them. Do not try to fix them.
7. If anything happens that these instructions do not cover, STOP and ask me.
   Do not improvise a workaround, switch data sources, or rewrite code to make
   something work.

## Step 1 — Check the environment

```bash
.venv/bin/python --version
.venv/bin/python -c "import pandas, requests, scipy, sklearn; print('deps OK')"
ls data/processed/ models/ data/raw/
```

If `scipy` or `requests` is missing, install only that package with
`.venv/bin/pip install <name>`. Confirm these files exist:
`data/processed/proteins_labeled.csv`, `data/processed/test_predictions.csv`,
`data/processed/clusters.csv`, `models/model_results.json`,
`models/model_results_random_split.json`, `data/raw/uniprot_kegg_xref.tsv`.
If any is missing, STOP and tell me which.

## Step 2 — Install the two updated files

I downloaded updated versions of `validate_kegg.py` and `config.py` into
`~/Downloads/`. Browsers sometimes rename duplicates, e.g. `config (1).py`.

1. Find them: `ls -lt ~/Downloads/*.py | head`. Pick the most recent
   `validate_kegg*.py` and `config*.py`. If you cannot find them, STOP and ask.
2. Verify they are the correct versions before copying. Each check must match:
   ```bash
   grep -n "^DOWNLOAD_RETRIES = 3" "<downloaded config>"
   grep -n "MIN_EXPECTED_EC_GENES" "<downloaded config>"
   grep -n "UNIPROT_STREAM_URL" "<downloaded config>"
   grep -n "def check_table" "<downloaded validate_kegg>"
   grep -n "def fetch_uniprot_kegg_xrefs" "<downloaded validate_kegg>"
   ```
   If any check fails, STOP and tell me which.
3. Show me `diff training/config.py "<downloaded config>"`. The expected
   differences are only: `DOWNLOAD_RETRIES` changing from 2 to 3, and new
   `MIN_EXPECTED_UNIPROT_LINKS`, `MIN_EXPECTED_EC_GENES`,
   `MIN_EXPECTED_PATHWAY_GENES` lines. If the diff shows anything else, STOP
   and show me before copying.
4. Back up, then copy:
   ```bash
   mkdir -p logs/backup
   cp training/config.py        logs/backup/config.py.bak
   cp training/validate_kegg.py logs/backup/validate_kegg.py.bak
   cp "<downloaded config>"        training/config.py
   cp "<downloaded validate_kegg>" training/validate_kegg.py
   .venv/bin/python -c "import ast; [ast.parse(open(f).read()) for f in ['training/config.py','training/validate_kegg.py']]; print('syntax OK')"
   ```

## Step 3 — Fetch the two KEGG tables with curl

Python's `requests` timed out reaching KEGG. Try `curl` instead. For each file,
make at most 3 attempts, waiting 60 seconds between attempts. Do not make more
attempts than that, and do not try other URLs, mirrors, or scraping.

```bash
curl -4 --max-time 600 -o data/raw/kegg_hsa_enzyme.tsv  https://rest.kegg.jp/link/enzyme/hsa
curl -4 --max-time 600 -o data/raw/kegg_hsa_pathway.tsv https://rest.kegg.jp/link/pathway/hsa
```

After each download, validate it:

```bash
head -3 data/raw/kegg_hsa_enzyme.tsv
wc -l   data/raw/kegg_hsa_enzyme.tsv
```

A valid enzyme file has lines like `hsa:10<TAB>ec:2.3.1.5` and well over 1,000
lines. A valid pathway file has lines like `hsa:10<TAB>path:hsa00232` and well
over 3,000 lines. If a file contains HTML, is empty, or is far too short, delete
that file and count it as a failed attempt.

If either file still fails after 3 attempts: STOP. Do not run step 4. Tell me
which file failed and what curl reported, and remind me I can open the URL in
Chrome, press Cmd+S, and save it to the exact path above.

## Step 4 — Run the KEGG validation

```bash
mkdir -p logs
.venv/bin/python training/validate_kegg.py 2>&1 | tee logs/validate_kegg.log
```

It should report every download as `cached`. If it makes a network request
instead, or exits with an error, STOP and show me the output.

## Step 5 — Cluster summary from the existing file (do NOT re-run MMseqs2)

```bash
.venv/bin/python - << 'EOF' | tee logs/cluster_summary.log
import pandas as pd
c = pd.read_csv("data/processed/clusters.csv")
lab = pd.read_csv("data/processed/proteins_labeled.csv")[["accession", "label"]]
c = c.merge(lab, on="accession")
sizes = c.groupby("cluster_id").size()
mixed = (c.groupby("cluster_id")["label"].nunique() > 1).sum()
multi = sizes[sizes > 1].sum()
print(f"Proteins                    : {len(c)}")
print(f"Clusters                    : {len(sizes)}")
print(f"Singletons                  : {(sizes == 1).sum()}")
print(f"Largest cluster             : {sizes.max()}")
print(f"Proteins in multi-member    : {multi} ({multi / len(c):.1%})")
print(f"Clusters mixing both labels : {mixed}")
EOF
```

## Step 6 — Write `docs/RESULTS_LOG.md`

Read values from files; do not retype them from memory. Create the report with
exactly these sections.

**1. Sequence clustering** — the output of step 5, verbatim.

**2. Random vs homology-aware split.** Build a table from the two JSON files.
The keys are:
- `models[<model name>]["test"]["roc_auc"]` and `["f1"]` for each model
- `best_model`
- `size_baseline["test"]["roc_auc"]` and `size_baseline["lift_of_full_model"]`
- `split_mode` (present only in `model_results.json`)

Columns: Model | ROC-AUC (random) | ROC-AUC (homology-aware) | Difference.
Include every model name that appears in both files. Then list best model,
size baseline and lift for each split. Use 4 decimal places.

**3. KEGG validation** — the full output of step 4, verbatim, excluding any
ResourceTracker messages.

**4. Files changed in this session** — list every file you created or
overwrote.

Do not add interpretation, conclusions, or recommendations. Report numbers only.

## Step 7 — Finish

Print a short summary in the terminal: which steps succeeded, the path to
`docs/RESULTS_LOG.md`, and any step where you stopped. Then stop.
