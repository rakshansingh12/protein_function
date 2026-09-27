# API reference

All routes are prefixed `/api`. The backend serves the frontend at `/` from
the same origin, so the UI calls these with relative URLs. Responses below
are taken from real requests against a running server.

## GET /api/health

```json
{"status":"ok","model_loaded":true}
```

`model_loaded` is `false` (still HTTP 200) when a required model artefact is
missing; every other route then returns 503 instead of crashing the server.

## GET /api/model-info

Final model name, split mode, selection rule, per-model test metrics
(ROC-AUC, F1, accuracy, precision, recall, plus the earlier random-split
ROC-AUC when that file exists), and the size-only baseline.

```json
{
  "best_model": "Extra Trees",
  "split_mode": "homology_aware",
  "selection_rule": "Ranked by cross-validated ROC-AUC, then F1, recall, accuracy. A simpler model within 0.005 ROC-AUC of the leader is preferred. An ensemble is adopted only if it exceeds the best individual model by more than 0.002 ROC-AUC.",
  "ensemble_selected": false,
  "training_dataset_size": 10782,
  "class_counts": {"enzyme": 5391, "non_enzyme": 5391},
  "models": {
    "Extra Trees": {
      "roc_auc": 0.8347015854873688,
      "f1": 0.7607476635514019,
      "accuracy": 0.755023923444976,
      "precision": 0.7509225092250923,
      "recall": 0.7708333333333334,
      "random_split_roc_auc": 0.8770252982817527
    }
  },
  "size_baseline": {
    "test_roc_auc": 0.6450649507649023,
    "lift_of_full_model": 0.1896366347224665
  }
}
```

Status codes: `200`. `503` if required model artefacts are missing.

## POST /api/predict

Body: `{"sequence": "<raw sequence, FASTA header allowed, max 20000 chars>"}`

Response fields: `prediction` (`"ENZYME"` / `"NON-ENZYME"`), `probability_enzyme`,
`confidence`, `model_name`, `sequence_length`, `cleaned_sequence`, `features`
(all 29, named), `comparison` (5 rows), `similar_proteins` (5 rows),
`motifs`, `dataset_match` (or `null`), `notes` (list of strings).

```json
{
  "prediction": "ENZYME",
  "probability_enzyme": 1.0,
  "confidence": 1.0,
  "model_name": "Extra Trees",
  "sequence_length": 1103,
  "dataset_match": {
    "accession": "O43896",
    "protein_name": "Kinesin-like protein KIF1C",
    "label": 1,
    "evidence_class": "GO_only",
    "in_training_split": true
  },
  "notes": [
    "The model was trained on reviewed human proteins only.",
    "Headline homology-aware ROC-AUC for Extra Trees: 0.8347.",
    "This protein was in the model's training split, so this result is not an independent test."
  ]
}
```

One `comparison` row:

```json
{
  "property": "isoelectric_point",
  "input": 6.470800971984862,
  "enzyme_mean": 7.180950680593031,
  "enzyme_std": 1.514636054567638,
  "non_enzyme_mean": 7.447883059668217,
  "non_enzyme_std": 1.8226595795511271
}
```

One `similar_proteins` row (`similarity = 100 / (1 + distance)`, training
split only):

```json
{"accession": "O43896", "class": "enzyme", "distance": 0.0, "similarity": 100.0}
```

`motifs.matches[0]` (class match rates are attached from `models/motif_stats.json`
when available):

```json
{
  "name": "Serine protease-related (simplified)",
  "start": 302,
  "end": 305,
  "match": "DSVL",
  "explanation": "A simplified approximation of the serine protease active-site motif...",
  "class_rates": {
    "enzyme_hits": 4574, "enzyme_total": 5391, "enzyme_pct": 0.8484511222407717,
    "non_enzyme_hits": 4245, "non_enzyme_total": 5391,
    "ratio_enzyme_over_non_enzyme": 1.078
  }
}
```

Status codes: `200`. `400` with `{"detail": "<validation message>"}` for an
empty, too-short, too-long, or non-standard-residue sequence. `503` if
required model artefacts are missing.

```
$ curl -X POST /api/predict -d '{"sequence":"HELLO"}' -> 400
{"detail":"Sequence is too short (5 residues). Minimum is 50; physicochemical estimates are unstable on very short fragments."}
```

## GET /api/enrich/{accession}

Supplementary UniProt, PDB, AlphaFold and KEGG records for an accession that
exactly matches a known protein. External sources fail independently and
silently (never a 5xx): a source that could not be reached comes back `null`.
KEGG is read from the precomputed `models/kegg_pathways.json`, never called
live.

```json
{
  "uniprot": {
    "protein_name": "Kinesin-like protein KIF1C",
    "organism": "Homo sapiens",
    "subcellular_locations": ["Cytoplasm, cytoskeleton"]
  },
  "pdb": [
    {"id": "2G1L", "method": "X-ray", "resolution": "2.60 A", "chains": "A=498-599", "url": "https://www.rcsb.org/structure/2G1L"}
  ],
  "alphafold": {"entry_id": "AF-O43896-F1", "mean_plddt": 67.75, "fraction_plddt_very_low": 0.279, "url": "https://alphafold.ebi.ac.uk/entry/O43896"},
  "kegg": {"genes": [{"gene": "hsa:10749", "url": "https://www.kegg.jp/entry/hsa:10749"}], "ec": [], "pathways": [{"id": "hsa04814", "name": "Motor proteins", "url": "https://www.kegg.jp/pathway/hsa04814"}]}
}
```

If every source is empty: `{"uniprot": null, "pdb": null, "alphafold": null,
"kegg": null, "message": "No additional database records found."}`

Status codes: `200`. `400` `{"detail":"Malformed UniProt accession."}` for a
badly formed accession. `404` `{"detail":"Accession is not in the dataset;
enrichment only runs for known proteins."}` for a well-formed accession
outside the dataset. `503` if required model artefacts are missing.

## Similarity formula

`similarity = 100 / (1 + distance)`, where `distance` is Euclidean distance
in the StandardScaler's scaled feature space, computed against the training
split only (the split the scaler and model were fit on). Monotonic,
explainable, bounded in `(0, 100]`; 100 means identical scaled features.

## Enrichment behaviour

Every external source (UniProt, AlphaFold) is wrapped so a timeout, HTTP
error, or malformed response degrades that one field to `null` rather than
failing the request. Results are cached in memory per accession for the life
of the server process. KEGG is never called live -- it reads the file built
by `training/build_kegg_pathways.py`.
