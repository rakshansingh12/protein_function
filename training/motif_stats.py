"""
Motif match rates by class: for each known motif, what fraction of enzymes
and of non-enzymes in the labelled dataset contain at least one match, and
the ratio of those two rates. A ratio near 1 means the motif carries little
class information in this dataset (it appears at similar rates in both
classes); a ratio far from 1 means the motif is informative.

Run:  .venv/bin/python training/motif_stats.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.services.motif_service import MOTIFS, scan_motifs

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


def main():
    df = pd.read_csv(config.PROCESSED_CSV)
    enzymes = df[df["label"] == config.LABEL_ENZYME]
    non_enzymes = df[df["label"] == config.LABEL_NON_ENZYME]

    def has_match(sequences, motif_name):
        count = 0
        for sequence in sequences:
            result = scan_motifs(sequence)
            names_found = {m["name"] for m in result["matches"]}
            if motif_name in names_found:
                count += 1
        return count

    print("Motif match rates by class")
    print("-" * 72)

    stats = {}
    for motif in MOTIFS:
        name = motif["name"]
        enz_hits = has_match(enzymes["sequence"], name)
        non_hits = has_match(non_enzymes["sequence"], name)
        enz_pct = enz_hits / len(enzymes)
        non_pct = non_hits / len(non_enzymes)
        ratio = enz_pct / non_pct if non_pct > 0 else float("inf")

        print(f"{name}:")
        print(f"  Enzymes     : {enz_hits} / {len(enzymes)} ({enz_pct:.1%})")
        print(f"  Non-enzymes : {non_hits} / {len(non_enzymes)} ({non_pct:.1%})")
        print(f"  Ratio (enzyme% / non-enzyme%): {ratio:.3f}")

        stats[name] = {
            "enzyme_hits": enz_hits,
            "enzyme_total": int(len(enzymes)),
            "enzyme_pct": enz_pct,
            "non_enzyme_hits": non_hits,
            "non_enzyme_total": int(len(non_enzymes)),
            "non_enzyme_pct": non_pct,
            "ratio_enzyme_over_non_enzyme": ratio,
        }

    out_path = Path(__file__).resolve().parents[1] / "models" / "motif_stats.json"
    out_path.write_text(json.dumps(stats, indent=2))
    print(f"\nSaved -> {out_path}")


if __name__ == "__main__":
    main()
