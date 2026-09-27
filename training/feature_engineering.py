"""
Step 3 of the pipeline: turn every cleaned sequence into a 29-feature row.

This script deliberately contains NO feature maths. It imports
backend/app/ml/feature_engineering.py, the same module the FastAPI server uses
at prediction time.

That single import is what guarantees train/inference consistency. If the
feature code were duplicated here, a change in one copy would silently produce
a model whose inputs no longer mean what it was trained on.

Run:  python training/feature_engineering.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# Make backend/ importable so the canonical feature module can be reused.
sys.path.insert(0, str(config.PROJECT_ROOT / "backend"))
from app.ml.feature_engineering import (  # noqa: E402
    FEATURE_NAMES,
    N_FEATURES,
    calculate_features,
)


def main():
    if not config.PROCESSED_CSV.exists():
        print(f"Processed file not found: {config.PROCESSED_CSV}")
        print("Run: python training/data_preprocessing.py")
        sys.exit(1)

    df = pd.read_csv(config.PROCESSED_CSV)
    print("=" * 72)
    print("FEATURE EXTRACTION")
    print("=" * 72)
    print(f"Input rows      : {len(df)}")
    print(f"Feature count   : {N_FEATURES}  (20 composition + 9 global)")

    rows = []
    failed = 0

    for record in df.to_dict("records"):
        try:
            features = calculate_features(record["sequence"])
        except Exception as exc:
            # Cleaning should have removed every problem case; count anything
            # that still fails rather than crashing the whole run.
            failed += 1
            if failed <= 5:
                print(f"  ! {record['accession']}: {exc}")
            continue

        row = {
            "accession": record["accession"],
            "label": record["label"],
            "evidence_class": record["evidence_class"],
        }
        row.update(dict(zip(FEATURE_NAMES, features)))
        rows.append(row)

    features_df = pd.DataFrame(rows)

    # Fixed column order: identity columns first, then the 29 features in
    # FEATURE_NAMES order. train.py relies on this ordering.
    column_order = ["accession", "label", "evidence_class"] + FEATURE_NAMES
    features_df = features_df[column_order]
    features_df.to_csv(config.FEATURES_CSV, index=False)

    print(f"\nExtracted       : {len(features_df)} rows")
    print(f"Failed          : {failed} rows")
    print(f"Matrix shape    : {features_df[FEATURE_NAMES].shape}")

    # Quick class-level look at the five dashboard properties. Useful in the
    # review: it shows the classes really do differ physicochemically, which is
    # why a classifier on these features is a reasonable idea at all.
    print("\nClass means (dashboard properties)")
    print("-" * 72)
    preview = ["isoelectric_point", "gravy", "molecular_weight",
               "aromaticity", "instability_index"]
    means = features_df.groupby("label")[preview].mean()
    means.index = means.index.map(config.LABEL_NAMES)
    print(means.round(3).to_string())

    print(f"\nSaved -> {config.FEATURES_CSV}")
    print("Next: python training/train.py")


if __name__ == "__main__":
    main()
