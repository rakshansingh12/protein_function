"""
Build models/kegg_pathways.json: per-accession KEGG genes, EC numbers and
named pathways, precomputed so the backend never has to call KEGG live
(KEGG times out on this network -- see validate_kegg.py).

Combines four already-downloaded tables:
  - data/raw/uniprot_kegg_xref.tsv    UniProt accession -> KEGG gene id
  - data/raw/kegg_hsa_enzyme.tsv      KEGG gene id -> EC number
  - data/raw/kegg_hsa_pathway.tsv     KEGG gene id -> pathway id
  - data/raw/kegg_hsa_pathway_names.tsv  pathway id -> human-readable name

Only accessions in the sequence index (models/sequence_index.json) are kept,
since those are the only proteins the backend can ever look up.

Run:  .venv/bin/python training/build_kegg_pathways.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
from validate_kegg import build_uniprot_to_genes, build_gene_to_values


PATHWAY_NAME_SUFFIX = " - Homo sapiens (human)"


def parse_pathway_names(text):
    """KEGG list output: `hsa01100<TAB>Metabolic pathways - Homo sapiens (human)`."""
    names = {}
    for line in text.strip().splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        pathway_id, name = parts[0].strip(), parts[1].strip()
        pathway_id = pathway_id[len("path:"):] if pathway_id.startswith("path:") else pathway_id
        if name.endswith(PATHWAY_NAME_SUFFIX):
            name = name[: -len(PATHWAY_NAME_SUFFIX)]
        names[pathway_id] = name
    return names


def main():
    sequence_index = json.loads(
        (Path(__file__).resolve().parents[1] / "models" / "sequence_index.json").read_text()
    )
    accessions = {entry["accession"] for entry in sequence_index.values()}

    uniprot_text = config.UNIPROT_KEGG_XREF.read_text()
    ec_text = config.KEGG_GENE_EC.read_text()
    pathway_text = config.KEGG_GENE_PATHWAY.read_text()
    names_text = (config.RAW_DIR / "kegg_hsa_pathway_names.tsv").read_text()

    uniprot_to_genes = build_uniprot_to_genes(uniprot_text)
    gene_to_ec = build_gene_to_values(ec_text, "ec:")
    gene_to_pathways = build_gene_to_values(pathway_text, "path:")
    pathway_names = parse_pathway_names(names_text)

    result = {}
    n_with_genes = 0
    n_with_ec = 0
    n_with_pathways = 0
    for accession in accessions:
        genes = sorted(uniprot_to_genes.get(accession, set()))
        if not genes:
            continue
        n_with_genes += 1

        ec_numbers = sorted({ec for gene in genes for ec in gene_to_ec.get(gene, set())})
        pathway_ids = sorted({p for gene in genes for p in gene_to_pathways.get(gene, set())})
        pathways = [
            {"id": pid, "name": pathway_names.get(pid, pid)} for pid in pathway_ids
        ]

        if ec_numbers:
            n_with_ec += 1
        if pathways:
            n_with_pathways += 1

        result[accession] = {
            "kegg_genes": genes,
            "ec": ec_numbers,
            "pathways": pathways,
        }

    out_path = Path(__file__).resolve().parents[1] / "models" / "kegg_pathways.json"
    out_path.write_text(json.dumps(result))

    print(f"Accessions in sequence index    : {len(accessions)}")
    print(f"Accessions with a KEGG gene      : {n_with_genes}")
    print(f"  with at least one EC number    : {n_with_ec}")
    print(f"  with at least one pathway      : {n_with_pathways}")
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()
