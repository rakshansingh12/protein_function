"""
Step 3b: group proteins into sequence families with MMseqs2.

WHY THIS STEP EXISTS
--------------------
data_preprocessing.py removes *identical* sequences. It does not remove
*similar* ones. The human proteome contains large families of related proteins
(paralogs): hundreds of kinases, proteases, zinc-finger proteins and so on,
many sharing 50-90% sequence identity.

Related proteins have nearly identical amino acid composition, so their 29
features are nearly identical too. With a random split, one family member can
sit in the training set while its sibling sits in the test set. The model then
scores well by recognising the family, not by learning what makes something an
enzyme. The test score is inflated, and nobody can tell by looking at it.

The standard fix in protein machine learning is to cluster sequences by
identity and keep each whole cluster on one side of every split. train.py does
this automatically once data/processed/clusters.csv exists.

REQUIREMENT: MMseqs2 must be installed and on your PATH.
    macOS    :  brew install mmseqs2
    conda    :  conda install -c conda-forge -c bioconda mmseqs2
    Linux    :  download a static binary from
                https://github.com/soedinglab/MMseqs2/releases

Run:  python training/cluster_sequences.py
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


def write_fasta(df, path):
    """Write accession + sequence pairs as FASTA, MMseqs2's input format."""
    with open(path, "w") as handle:
        for accession, sequence in zip(df["accession"], df["sequence"]):
            handle.write(f">{accession}\n{sequence}\n")


def run_mmseqs(fasta_path, work_dir):
    """
    Run `mmseqs easy-cluster` and return the path to its cluster table.

    Parameters, all set in config.py:
      --min-seq-id  minimum fraction of identical residues to join a cluster
      -c            minimum alignment coverage
      --cov-mode 0  coverage must hold for BOTH sequences, so a short protein
                    that matches one domain of a long one is not merged with it
    """
    output_prefix = work_dir / "clusters"
    tmp_dir = work_dir / "tmp"

    command = [
        "mmseqs", "easy-cluster",
        str(fasta_path), str(output_prefix), str(tmp_dir),
        "--min-seq-id", str(config.CLUSTER_MIN_SEQ_ID),
        "-c", str(config.CLUSTER_COVERAGE),
        "--cov-mode", "0",
        "-v", "1",
    ]
    print("Running: " + " ".join(command))
    subprocess.run(command, check=True)

    # easy-cluster writes <prefix>_cluster.tsv: representative<TAB>member
    return Path(f"{output_prefix}_cluster.tsv")


def main():
    if shutil.which("mmseqs") is None:
        print("MMseqs2 is not installed or not on your PATH.")
        print("  macOS : brew install mmseqs2")
        print("  conda : conda install -c conda-forge -c bioconda mmseqs2")
        sys.exit(1)

    if not config.PROCESSED_CSV.exists():
        print(f"Processed file not found: {config.PROCESSED_CSV}")
        print("Run: python training/data_preprocessing.py")
        sys.exit(1)

    df = pd.read_csv(config.PROCESSED_CSV)

    print("=" * 72)
    print("SEQUENCE CLUSTERING (MMseqs2)")
    print("=" * 72)
    print(f"Proteins          : {len(df)}")
    print(f"Min seq identity  : {config.CLUSTER_MIN_SEQ_ID}")
    print(f"Min coverage      : {config.CLUSTER_COVERAGE}")

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        fasta_path = work_dir / "proteins.fasta"
        write_fasta(df, fasta_path)
        cluster_tsv = run_mmseqs(fasta_path, work_dir)

        pairs = pd.read_csv(
            cluster_tsv, sep="\t", header=None,
            names=["representative", "accession"],
        )

    # The representative's accession serves as the cluster id.
    clusters = pairs.rename(columns={"representative": "cluster_id"})
    clusters = clusters[["accession", "cluster_id"]]

    # Attach labels so we can see whether families mix enzymes and non-enzymes.
    clusters = clusters.merge(df[["accession", "label"]], on="accession")

    sizes = clusters.groupby("cluster_id").size()
    mixed = clusters.groupby("cluster_id")["label"].nunique()
    mixed_clusters = int((mixed > 1).sum())

    print("\n" + "-" * 72)
    print("CLUSTER SUMMARY")
    print("-" * 72)
    print(f"Clusters                    : {len(sizes)}")
    print(f"Singletons (size 1)         : {int((sizes == 1).sum())}")
    print(f"Largest cluster             : {int(sizes.max())} proteins")
    print(f"Proteins in multi-member    : {int(sizes[sizes > 1].sum())} "
          f"({sizes[sizes > 1].sum() / len(clusters):.1%})")
    print(f"Clusters mixing both labels : {mixed_clusters}")

    print("\nLargest five clusters:")
    for cluster_id, size in sizes.sort_values(ascending=False).head(5).items():
        members = clusters[clusters["cluster_id"] == cluster_id]
        enzymes = int((members["label"] == config.LABEL_ENZYME).sum())
        print(f"  {cluster_id:<12} {size:>4} proteins  "
              f"({enzymes} enzyme / {size - enzymes} non-enzyme)")

    print(
        "\nThe share of proteins in multi-member clusters is how much of the\n"
        "dataset could leak between train and test under a random split."
    )

    clusters[["accession", "cluster_id"]].to_csv(config.CLUSTERS_CSV, index=False)
    print(f"\nSaved -> {config.CLUSTERS_CSV}")
    print("Next: python training/train.py   (now runs a homology-aware split)")


if __name__ == "__main__":
    main()