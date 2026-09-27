"""
AlphaFold pLDDT analysis (analysis only, never a model feature).

Purpose: test whether non-enzymes are more disordered than enzymes, which
would explain their higher instability index (see RESULTS_LOG). AlphaFold
structures are RETRIEVED (precomputed), never predicted here, and pLDDT is
AlphaFold's own prediction confidence -- a proxy for disorder, not disorder
itself. This script never feeds AlphaFold data back into the classifier: it
is only available for proteins already in UniProt, so using it as a feature
would be circular.

Groups (seed 42, see config.RANDOM_SEED):
  - GO_only:   all proteins with evidence_class == "GO_only"
  - EC_backed: random 1,000 proteins with evidence_class in
               {EC_and_GO, EC_only}
  - non_enzyme: random 1,000 proteins with label == non-enzyme

For each accession we fetch (or reuse a cached copy of) the AlphaFold
prediction, take the entry ending in "-F1" (the first/only fragment for most
human proteins) or the first entry otherwise, and record:
  - mean_plddt   = globalMetricValue
  - frac_very_low = fractionPlddtVeryLow

Run:  .venv/bin/python training/alphafold_analysis.py
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy.stats import mannwhitneyu, spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


def build_groups(labeled_df):
    """Select the three comparison groups, seeded for reproducibility."""
    rng_seed = config.RANDOM_SEED

    go_only = labeled_df[labeled_df["evidence_class"] == "GO_only"]

    ec_backed_pool = labeled_df[
        labeled_df["evidence_class"].isin(["EC_and_GO", "EC_only"])
    ]
    ec_backed = ec_backed_pool.sample(
        n=min(1000, len(ec_backed_pool)), random_state=rng_seed
    )

    non_enzyme_pool = labeled_df[labeled_df["label"] == config.LABEL_NON_ENZYME]
    non_enzyme = non_enzyme_pool.sample(
        n=min(1000, len(non_enzyme_pool)), random_state=rng_seed
    )

    return {
        "GO_only": go_only["accession"].tolist(),
        "EC_backed": ec_backed["accession"].tolist(),
        "non_enzyme": non_enzyme["accession"].tolist(),
    }


def fetch_alphafold(accession):
    """
    Return the AlphaFold prediction record for one accession, using the disk
    cache when present. Only HTTP 404 (no structure) is cached as a miss;
    every other error is left uncached so a later run can retry it.
    """
    config.ALPHAFOLD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = config.ALPHAFOLD_CACHE_DIR / f"{accession}.json"

    if cache_path.exists():
        return json.loads(cache_path.read_text())

    url = f"{config.ALPHAFOLD_API_URL}/{accession}"
    last_error = None
    for attempt in range(1, 3):
        try:
            response = requests.get(url, timeout=(10, 30))
        except requests.RequestException as exc:
            last_error = str(exc)
            time.sleep(0.1)
            continue

        if response.status_code == 404:
            record = {"missing": True}
            cache_path.write_text(json.dumps(record))
            return record

        if response.status_code == 200:
            record = response.json()
            cache_path.write_text(json.dumps(record))
            return record

        last_error = f"HTTP {response.status_code}"
        time.sleep(0.1)

    return {"error": last_error}


def extract_metrics(record):
    """Pick the -F1 entry (or the first entry) and pull out the two metrics."""
    if not isinstance(record, list) or not record:
        return None

    entry = next((e for e in record if str(e.get("entryId", "")).endswith("-F1")), record[0])
    mean_plddt = entry.get("globalMetricValue")
    frac_very_low = entry.get("fractionPlddtVeryLow")
    if mean_plddt is None or frac_very_low is None:
        return None
    return {"mean_plddt": mean_plddt, "frac_very_low": frac_very_low}


def collect_group_data(name, accessions):
    """Fetch AlphaFold metrics for one group, printing progress every 100."""
    rows = []
    n_missing = 0
    n_failed = 0

    for i, accession in enumerate(accessions, start=1):
        record = fetch_alphafold(accession)

        if isinstance(record, dict) and record.get("missing"):
            n_missing += 1
        elif isinstance(record, dict) and "error" in record:
            n_failed += 1
        else:
            metrics = extract_metrics(record)
            if metrics is None:
                n_missing += 1
            else:
                rows.append({"accession": accession, **metrics})

        if i % 100 == 0:
            print(f"  [{name}] {i} / {len(accessions)} processed")

    print(f"  [{name}] done: {len(rows)} with data, {n_missing} missing, "
          f"{n_failed} failed")
    return pd.DataFrame(rows), n_missing, n_failed


def describe(series):
    """Median and IQR (Q1, Q3) for a numeric series."""
    return {
        "median": float(series.median()),
        "q1": float(series.quantile(0.25)),
        "q3": float(series.quantile(0.75)),
    }


def probability_of_superiority(a, b):
    """P(a random value from group a > a random value from group b)."""
    u_stat, _ = mannwhitneyu(a, b, alternative="greater")
    return float(u_stat / (len(a) * len(b)))


def compare_groups(name_a, a, name_b, b, column):
    """Mann-Whitney U (two-sided) plus probability of superiority for a > b."""
    stat, p_value = mannwhitneyu(a[column], b[column], alternative="two-sided")
    pos = probability_of_superiority(a[column], b[column])
    return {
        "comparison": f"{name_a} vs {name_b}",
        "metric": column,
        "u_statistic": float(stat),
        "p_value": float(p_value),
        # "the chance a random protein from group A scores higher than one
        # from group B"
        "probability_of_superiority_a_over_b": pos,
    }


def main():
    print("=" * 72)
    print("ALPHAFOLD pLDDT ANALYSIS (analysis only, not a model feature)")
    print("=" * 72)

    labeled_df = pd.read_csv(config.PROCESSED_DIR / "proteins_labeled.csv")
    features_df = pd.read_csv(config.PROCESSED_DIR / "features.csv")

    groups_accessions = build_groups(labeled_df)

    group_data = {}
    for name, accessions in groups_accessions.items():
        print(f"\nFetching AlphaFold data for group '{name}' "
              f"({len(accessions)} proteins)...")
        df, n_missing, n_failed = collect_group_data(name, accessions)
        df = df.merge(
            features_df[["accession", "instability_index"]],
            on="accession", how="left",
        )
        group_data[name] = {
            "df": df,
            "n_requested": len(accessions),
            "n_with_data": len(df),
            "n_missing": n_missing,
            "n_failed": n_failed,
        }

    total_requests = sum(g["n_requested"] for g in group_data.values())
    total_failed = sum(g["n_failed"] for g in group_data.values())
    failure_rate = total_failed / total_requests if total_requests else 0.0
    print(f"\nOverall non-404 failure rate: {total_failed} / {total_requests} "
          f"({failure_rate:.1%})")
    if failure_rate > 0.10:
        print("FAILURE RATE EXCEEDS 10%. Stopping (cached results are kept).")
        sys.exit(1)

    print("\n" + "=" * 72)
    print("PER-GROUP SUMMARY")
    print("=" * 72)
    summary = {}
    for name, g in group_data.items():
        df = g["df"]
        mean_plddt_stats = describe(df["mean_plddt"])
        frac_very_low_stats = describe(df["frac_very_low"])
        print(f"\n{name}:")
        print(f"  n requested        : {g['n_requested']}")
        print(f"  n with AlphaFold    : {g['n_with_data']}")
        print(f"  n missing           : {g['n_missing']}")
        print(f"  mean_plddt   median : {mean_plddt_stats['median']:.2f} "
              f"(IQR {mean_plddt_stats['q1']:.2f}-{mean_plddt_stats['q3']:.2f})")
        print(f"  frac_very_low median: {frac_very_low_stats['median']:.4f} "
              f"(IQR {frac_very_low_stats['q1']:.4f}-{frac_very_low_stats['q3']:.4f})")
        summary[name] = {
            "n_requested": g["n_requested"],
            "n_with_data": g["n_with_data"],
            "n_missing": g["n_missing"],
            "mean_plddt": mean_plddt_stats,
            "frac_very_low": frac_very_low_stats,
        }

    print("\n" + "=" * 72)
    print("STATISTICAL COMPARISONS")
    print("=" * 72)
    pairs = [
        ("EC_backed", "non_enzyme"),
        ("GO_only", "EC_backed"),
        ("GO_only", "non_enzyme"),
    ]
    comparisons = []
    for name_a, name_b in pairs:
        a = group_data[name_a]["df"]
        b = group_data[name_b]["df"]
        for column in ["mean_plddt", "frac_very_low"]:
            result = compare_groups(name_a, a, name_b, b, column)
            comparisons.append(result)
            print(f"  {result['comparison']:<24} {column:<16} "
                  f"p={result['p_value']:.4g}  "
                  f"P(superiority)={result['probability_of_superiority_a_over_b']:.3f}")

    print("\n" + "=" * 72)
    print("INSTABILITY INDEX vs PREDICTED DISORDER")
    print("=" * 72)
    all_rows = pd.concat([g["df"] for g in group_data.values()], ignore_index=True)
    all_rows = all_rows.dropna(subset=["instability_index", "frac_very_low"])
    rho, spearman_p = spearmanr(all_rows["instability_index"], all_rows["frac_very_low"])
    print(f"  Spearman rho = {rho:.4f}, p = {spearman_p:.4g} "
          f"(n = {len(all_rows)})")

    report = {
        "groups": summary,
        "comparisons": comparisons,
        "spearman_instability_vs_frac_very_low": {
            "rho": float(rho),
            "p_value": float(spearman_p),
            "n": int(len(all_rows)),
        },
        "caveat": ("pLDDT is AlphaFold's prediction confidence, a proxy for "
                   "disorder, not a direct measurement of it."),
    }
    config.ALPHAFOLD_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    config.ALPHAFOLD_REPORT_JSON.write_text(json.dumps(report, indent=2))
    print(f"\nSaved -> {config.ALPHAFOLD_REPORT_JSON}")


if __name__ == "__main__":
    main()
