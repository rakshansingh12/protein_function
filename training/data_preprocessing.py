"""
Step 2 of the pipeline: clean the raw download and finalise the consensus label.

Cleaning rules and why each exists:

  1. Drop sequences containing non-standard residues (X, B, Z, J, U, O).
     BioPython's ProtParam cannot compute molecular weight or GRAVY for
     ambiguous codes, so these rows cannot be featurised at all.

  2. Apply a length window (config.MIN/MAX_SEQUENCE_LENGTH).
     Very short peptides give unstable physicochemical estimates; very long
     multi-domain proteins have global composition that averages away any
     functional signal.

  3. Remove duplicate accessions, then duplicate *sequences*.
     Identical sequences under different accessions (isoforms, redundant
     entries) would otherwise leak between the train and test split and
     inflate the reported scores.

  4. Balance the classes by downsampling the majority class.
     Keeps accuracy interpretable and stops the models from learning the prior.

The script prints the exact transparency block the methodology requires:
total / EC-only / GO-only / both / neither / final enzyme / final non-enzyme.

Run:  python training/data_preprocessing.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


def has_only_standard_residues(sequence):
    """True if every residue is one of the 20 standard amino acids."""
    if not isinstance(sequence, str) or not sequence:
        return False
    return set(sequence.upper()) <= set(config.STANDARD_AMINO_ACIDS)


def summarise(df, stage):
    """Print a one-line class breakdown. Called after every cleaning step."""
    enzymes = int((df["label"] == config.LABEL_ENZYME).sum())
    non_enzymes = int((df["label"] == config.LABEL_NON_ENZYME).sum())
    print(
        f"  {stage:<38} rows={len(df):>6}  "
        f"enzyme={enzymes:>5}  non-enzyme={non_enzymes:>5}"
    )


def balance_classes(df, seed, max_per_class=None):
    """
    Downsample the larger class to match the smaller one, optionally capping
    both classes at max_per_class.

    Downsampling rather than upsampling: duplicating minority rows would put
    near-identical proteins on both sides of the train/test split, which is a
    subtle form of leakage.

    This runs AFTER the evidence-class counts have been computed, so capping
    here can never distort the labeling report.
    """
    counts = df["label"].value_counts()
    if len(counts) < 2:
        return df

    target = int(counts.min())
    if max_per_class is not None:
        target = min(target, int(max_per_class))

    frames = [
        group.sample(n=target, random_state=seed)
        for _, group in df.groupby("label")
    ]
    balanced = pd.concat(frames, ignore_index=True)
    return balanced.sample(frac=1.0, random_state=seed).reset_index(drop=True)


def main():
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if not config.RAW_COMBINED_CSV.exists():
        print(f"Raw file not found: {config.RAW_COMBINED_CSV}")
        print("Run: python training/download_data.py")
        sys.exit(1)

    df = pd.read_csv(config.RAW_COMBINED_CSV)
    df["sequence"] = df["sequence"].astype(str).str.upper().str.strip()

    print("=" * 72)
    print("DATA CLEANING")
    print("=" * 72)
    summarise(df, "loaded raw")

    # 1. Deduplicate by accession (defensive; download already does this).
    df = df.drop_duplicates(subset="accession", keep="first")
    summarise(df, "after accession dedup")

    # 2. Drop non-standard residues.
    before = len(df)
    df = df[df["sequence"].apply(has_only_standard_residues)]
    print(f"  dropped {before - len(df)} rows with non-standard residues "
          f"({config.NON_STANDARD_RESIDUES})")
    summarise(df, "after residue filter")

    # 3. Length window.
    before = len(df)
    df = df[
        (df["sequence"].str.len() >= config.MIN_SEQUENCE_LENGTH)
        & (df["sequence"].str.len() <= config.MAX_SEQUENCE_LENGTH)
    ]
    print(f"  dropped {before - len(df)} rows outside "
          f"[{config.MIN_SEQUENCE_LENGTH}, {config.MAX_SEQUENCE_LENGTH}] "
          f"residues")
    summarise(df, "after length filter")

    # 4. Deduplicate identical sequences (leakage prevention).
    before = len(df)
    df = df.drop_duplicates(subset="sequence", keep="first")
    print(f"  dropped {before - len(df)} exact duplicate sequences")
    summarise(df, "after sequence dedup")

    # ---- Evidence breakdown BEFORE balancing ------------------------------
    # Reported on the cleaned-but-unbalanced set, because this is the honest
    # picture of how much each annotation source contributed.
    counts = df["evidence_class"].value_counts().to_dict()
    ec_only = int(counts.get(config.EVIDENCE_EC_ONLY, 0))
    go_only = int(counts.get(config.EVIDENCE_GO_ONLY, 0))
    both = int(counts.get(config.EVIDENCE_BOTH, 0))
    neither = int(counts.get(config.EVIDENCE_NEITHER, 0))

    # 5. Balance.
    df = balance_classes(df, config.RANDOM_SEED, config.MAX_PER_CLASS)
    summarise(df, "after class balancing")

    final_enzyme = int((df["label"] == config.LABEL_ENZYME).sum())
    final_non_enzyme = int((df["label"] == config.LABEL_NON_ENZYME).sum())

    # ---- Required transparency block --------------------------------------
    print("\n" + "=" * 72)
    print("CONSENSUS LABELING REPORT")
    print("=" * 72)
    print(f"Total proteins (cleaned)   : {ec_only + go_only + both + neither}")
    print(f"EC-only                    : {ec_only}")
    print(f"GO-only                    : {go_only}")
    print(f"Both EC + GO               : {both}")
    print(f"Neither                    : {neither}")
    print("-" * 72)
    print(f"Final enzyme count         : {final_enzyme}")
    print(f"Final non-enzyme count     : {final_non_enzyme}")
    print("=" * 72)
    print(
        "\nInterpretation: the GO-only count is the number of proteins the "
        "\noriginal EC-presence-only scheme would have mislabelled as "
        "non-enzymes."
    )

    # Guard against reporting numbers derived from a truncated download.
    if config.DOWNLOAD_MAX_PER_QUERY is not None:
        print(
            "\n! WARNING: DOWNLOAD_MAX_PER_QUERY is set, so at least one "
            "UniProt query\n! may have been truncated. The EC-only / GO-only "
            "split above is then\n! unreliable: missing GO entries are counted "
            "as EC-only instead of both.\n! Set DOWNLOAD_MAX_PER_QUERY = None "
            "and re-download before reporting."
        )

    # ---- Save -------------------------------------------------------------
    keep_columns = [
        "accession", "protein_name", "organism", "sequence", "length",
        "ec_numbers", "go_ids", "has_ec", "has_go_catalytic",
        "evidence_class", "label",
    ]
    df = df[[c for c in keep_columns if c in df.columns]]
    df.to_csv(config.PROCESSED_CSV, index=False)

    report = {
        "total_proteins_cleaned": ec_only + go_only + both + neither,
        "ec_only": ec_only,
        "go_only": go_only,
        "both_ec_and_go": both,
        "neither": neither,
        "final_enzyme_count": final_enzyme,
        "final_non_enzyme_count": final_non_enzyme,
        "mislabelled_by_ec_only_scheme": go_only,
        "filters": {
            "reviewed_only": config.REVIEWED_ONLY,
            "organism_id": config.ORGANISM_ID,
            "min_sequence_length": config.MIN_SEQUENCE_LENGTH,
            "max_sequence_length": config.MAX_SEQUENCE_LENGTH,
            "standard_residues_only": True,
            "class_balanced": True,
        },
    }
    with open(config.LABELING_REPORT_JSON, "w") as handle:
        json.dump(report, handle, indent=2)

    print(f"\nSaved -> {config.PROCESSED_CSV}")
    print(f"Saved -> {config.LABELING_REPORT_JSON}")
    print("Next: python training/feature_engineering.py")


if __name__ == "__main__":
    main()