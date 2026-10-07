"""
Per-class mean and standard deviation for ALL 29 features, for the
"where does this protein sit" comparison dashboard.

train.py wrote class_stats.json for only 5 headline properties. This script
extends that to every feature WITHOUT re-running training: it takes the exact
training-split accessions saved in training_features.joblib, looks up their
raw (unscaled) features in features.csv, and applies the same computation as
train.compute_class_stats (pandas mean and std). Training split only, so the
test set stays untouched.

Sanity check: the 5 properties already in class_stats.json must come out
identical, which proves we used the same rows and the same feature values.

Run:  .venv/bin/python training/class_stats_all.py
"""

import json
import math
import sys
from pathlib import Path

import joblib
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.ml.feature_engineering import FEATURE_NAMES

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


def main():
    features = pd.read_csv(config.FEATURES_CSV)
    training = joblib.load(config.MODELS_DIR / "training_features.joblib")
    train_accessions = set(training["accessions"])
    df_train = features[features["accession"].isin(train_accessions)]

    if len(df_train) != len(train_accessions):
        sys.exit(f"STOP: matched {len(df_train)} rows for {len(train_accessions)} training accessions")

    stats = {}
    for label_value, label_name in config.LABEL_NAMES.items():
        subset = df_train[df_train["label"] == label_value]
        stats[label_name] = {
            prop: {
                "mean": float(subset[prop].mean()),
                "std": float(subset[prop].std()),
            }
            for prop in FEATURE_NAMES
        }
        stats[label_name]["count"] = int(len(subset))

    # Must reproduce the existing headline stats exactly.
    existing = json.loads((config.MODELS_DIR / "class_stats.json").read_text())
    for label_name, props in existing.items():
        if props["count"] != stats[label_name]["count"]:
            sys.exit(f"STOP: {label_name} count {stats[label_name]['count']} != {props['count']}")
        for prop, values in props.items():
            if prop == "count":
                continue
            for key in ("mean", "std"):
                ours = stats[label_name][prop][key]
                if not math.isclose(ours, values[key], rel_tol=1e-9, abs_tol=0):
                    sys.exit(f"STOP: {label_name}.{prop}.{key} {ours} != {values[key]}")
    print("Sanity check passed: the 5 existing properties match class_stats.json")

    with open(config.CLASS_STATS_ALL_JSON, "w") as handle:
        json.dump(stats, handle, indent=2)

    print(f"Training rows: {len(df_train)}  "
          f"(enzyme {stats['enzyme']['count']}, non_enzyme {stats['non_enzyme']['count']})")
    print(f"Wrote {len(FEATURE_NAMES)} features x 2 classes to {config.CLASS_STATS_ALL_JSON}")


if __name__ == "__main__":
    main()
