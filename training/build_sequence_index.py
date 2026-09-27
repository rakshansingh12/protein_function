"""
Build a lookup from cleaned-sequence hash to known protein metadata.

The backend uses this to recognise when a submitted sequence is an EXACT
match to a protein already in our reviewed human proteome (all 20,430,
before balancing), so it can show a "this is a known protein" banner instead
of treating every submission as novel.

Key: SHA-256 hex digest of clean_sequence(sequence) -- hashing means we never
store or compare raw sequences directly, and collisions are effectively
impossible for protein-length strings.

Run:  .venv/bin/python training/build_sequence_index.py
"""

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.ml.feature_engineering import clean_sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


def main():
    df = pd.read_csv(config.RAW_DIR / "uniprot_raw_combined.csv")

    index = {}
    collisions = 0
    for row in df.itertuples():
        cleaned = clean_sequence(row.sequence)
        digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
        if digest in index:
            collisions += 1
            continue
        index[digest] = {
            "accession": row.accession,
            "protein_name": row.protein_name,
            "label": int(row.label),
            "evidence_class": row.evidence_class,
        }

    out_path = Path(__file__).resolve().parents[1] / "models" / "sequence_index.json"
    out_path.write_text(json.dumps(index))

    print(f"Proteins processed          : {len(df)}")
    print(f"Unique sequence hashes       : {len(index)}")
    print(f"Duplicate-sequence collisions: {collisions}")
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()
