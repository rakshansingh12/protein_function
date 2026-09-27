"""
Step 5: validate the consensus labels against KEGG, an independent database.

This script asks two questions.

QUESTION 1 — Do our labels agree with KEGG?
    KEGG assigns EC numbers to human genes through its own orthology system
    (KEGG Orthology, KO): a gene inherits an EC number when it belongs to an
    ortholog group containing characterised enzymes. That is a different
    evidence route from UniProt's curated EC and GO annotations, so it is a
    meaningful cross-check. We measure:
      - what fraction of our enzymes KEGG also treats as enzymes
      - how many of our non-enzymes KEGG treats as enzymes
    The second group are candidate mislabels: proteins where UniProt EC and
    catalytic GO are both silent, but KEGG orthology says "enzyme".

QUESTION 2 — Are the model's false positives really errors?
    The trained model calls some non-enzymes "enzyme". If our negative class
    still contains under-annotated enzymes, those should be over-represented
    among these false positives. We test that with Fisher's exact test:
    among true-labelled non-enzymes in the test set, is KEGG enzyme evidence
    more common in the ones the model called "enzyme" than in the ones it
    called "non-enzyme"?

    If yes, part of the model's apparent error rate is label noise, and the
    model is detecting enzymes that the annotations missed. If no, the false
    positives are ordinary model errors. Either answer is reported honestly.

KEGG is not used to change any label. It is a validation source only.

Data use: the KEGG REST API is for academic, non-commercial use.
One UniProt request and two KEGG bulk requests are made, all cached in
data/raw/. The UniProt->KEGG mapping comes from UniProt's own cross-references.

Run:  python training/validate_kegg.py
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from scipy.stats import fisher_exact

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


# ---------------------------------------------------------------------------
# Downloads (one UniProt call + two KEGG calls, all cached)
# ---------------------------------------------------------------------------
def download_with_retry(url, cache_path, params=None, label="GET"):
    """
    Download a large text table with retries, or read it from cache.

    Bulk tables can be several megabytes and KEGG's servers are slow from some
    networks, so a single request with a fixed timeout is fragile. We use:
      - a short CONNECT timeout (fail fast if the server is unreachable)
      - a long READ timeout (a slow but working transfer is allowed to finish)
      - streaming, so the timeout applies per chunk rather than to the whole file
      - up to config.DOWNLOAD_RETRIES attempts with increasing waits
    A successful download is cached, so it never has to be repeated.
    """
    if cache_path.exists():
        print(f"  cached  {cache_path.name}")
        return cache_path.read_text()

    last_error = None
    for attempt in range(1, config.DOWNLOAD_RETRIES + 1):
        try:
            print(f"  {label:<7} {url}  (attempt {attempt}/{config.DOWNLOAD_RETRIES})")
            with requests.get(url, params=params, stream=True,
                              timeout=config.DOWNLOAD_TIMEOUT) as response:
                response.raise_for_status()
                chunks = []
                for chunk in response.iter_content(chunk_size=65536,
                                                   decode_unicode=True):
                    chunks.append(chunk)
            text = "".join(chunks)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(text)
            print(f"          saved {len(text) / 1e6:.1f} MB -> {cache_path.name}")
            return text
        except requests.RequestException as exc:
            last_error = exc
            wait = 10 * attempt
            print(f"          failed: {exc.__class__.__name__}. "
                  + (f"Retrying in {wait}s." if attempt < config.DOWNLOAD_RETRIES else ""))
            if attempt < config.DOWNLOAD_RETRIES:
                time.sleep(wait)

    # All attempts failed: explain the manual fallback rather than just crashing.
    full_url = requests.Request("GET", url, params=params).prepare().url
    print(f"\nCould not download {cache_path.name} after "
          f"{config.DOWNLOAD_RETRIES} attempts ({last_error.__class__.__name__}).")
    print("Manual fallback: open this URL in your browser, save the page as")
    print(f"plain text to the path below, then re-run this script.")
    print(f"  URL : {full_url}")
    print(f"  Save: {cache_path}")
    sys.exit(1)


def fetch_uniprot_kegg_xrefs():
    """
    UniProt accession -> KEGG gene id mapping, taken from UniProt itself.

    Every UniProt entry carries cross-references to other databases. The
    `xref_kegg` return field gives each protein's KEGG gene id (e.g. hsa:760
    for carbonic anhydrase 2). The UniProt stream endpoint returns all ~20,000
    reviewed human entries in one response.

    We use this rather than KEGG's own conv endpoint because the conv table is
    large and KEGG's servers frequently time out on it, while UniProt serves
    the same mapping quickly. It is also a cleaner database-integration story:
    the link from UniProt to KEGG is maintained by UniProt.
    """
    query_parts = []
    if config.REVIEWED_ONLY:
        query_parts.append("(reviewed:true)")
    query_parts.append(f"(organism_id:{config.ORGANISM_ID})")
    params = {
        "query": " AND ".join(query_parts),
        "fields": "accession,xref_kegg",
        "format": "tsv",
    }
    return download_with_retry(
        config.UNIPROT_STREAM_URL, config.UNIPROT_KEGG_XREF,
        params=params, label="UniProt",
    )


def fetch_kegg_table(endpoint, cache_path):
    """One KEGG bulk table (the entire human mapping in a single response)."""
    return download_with_retry(
        f"{config.KEGG_BASE_URL}/{endpoint}", cache_path, label="KEGG",
    )


def parse_pairs(text):
    """KEGG link output: one tab-separated pair per line."""
    pairs = []
    for line in text.strip().splitlines():
        parts = line.split("\t")
        if len(parts) == 2:
            pairs.append((parts[0].strip(), parts[1].strip()))
    return pairs


def build_uniprot_to_genes(text):
    """
    Parse the UniProt TSV into accession -> set of KEGG gene ids.

    The file has a header row, then one protein per line:
        P00918<TAB>hsa:760;
    Proteins with no KEGG link have an empty second column. A few proteins
    link to more than one KEGG gene, separated by semicolons.
    """
    mapping = {}
    lines = text.strip().splitlines()
    for line in lines[1:]:                      # skip header
        parts = line.split("\t")
        if len(parts) < 2 or not parts[1].strip():
            continue
        genes = {g.strip() for g in parts[1].split(";") if g.strip()}
        if genes:
            mapping[parts[0].strip()] = genes
    return mapping


def build_gene_to_values(text, prefix):
    """
    Map KEGG gene id -> set of linked ids, e.g. hsa:760 -> {"4.2.1.1"}.

    Only rows that genuinely look like KEGG link output are accepted: one side
    must be a human gene id (hsa:...) and the other must carry the expected
    prefix (ec: or path:). Anything else, such as the HTML of an error page, is
    ignored, so a bad file produces an empty mapping that check_table() catches.
    """
    mapping = {}
    for left, right in parse_pairs(text):
        if left.startswith("hsa:") and right.startswith(prefix):
            gene, value = left, right
        elif right.startswith("hsa:") and left.startswith(prefix):
            gene, value = right, left
        else:
            continue
        mapping.setdefault(gene, set()).add(value[len(prefix):])
    return mapping


def check_table(mapping, path, example, expected_minimum):
    """
    Refuse to continue on an empty or implausibly small table.

    A cached file is trusted on the next run, and the manual fallback asks you
    to save files by hand, so a browser error page or a truncated download
    could otherwise be parsed as "KEGG knows no enzymes" and quietly produce a
    wrong result that looks like a real one.
    """
    if not mapping:
        print(f"\n{path.name} exists but contains no valid rows.")
        print(f"Expected lines like:  {example}")
        print("It is probably an HTML error page or an empty download.")
        print(f"Delete it and download again:\n  rm {path}")
        sys.exit(1)
    if len(mapping) < expected_minimum:
        print(f"\n  ! {path.name}: only {len(mapping)} entries "
              f"(expected {expected_minimum}+ for human). The download may be "
              f"truncated; if results look odd, delete it and re-download.")


def is_metabolic(pathway_id):
    """
    True for KEGG pathways in the Metabolism category.

    Pathway ids look like 'hsa00010' (glycolysis). Map numbers below 01300 are
    metabolic. Signalling pathways (04xxx) and disease pathways (05xxx) are
    excluded, because receptors and adaptor proteins appear in those without
    being enzymes.
    """
    digits = "".join(ch for ch in pathway_id if ch.isdigit())
    return bool(digits) and int(digits) < config.KEGG_METABOLIC_MAX


def annotate_with_kegg(df, uniprot_to_genes, gene_to_ec, gene_to_pathways):
    """Add KEGG evidence columns to a protein table."""
    in_kegg, kegg_ec, n_metabolic = [], [], []

    for accession in df["accession"]:
        genes = uniprot_to_genes.get(accession, set())
        ec_numbers, metabolic = set(), set()
        for gene in genes:
            ec_numbers |= gene_to_ec.get(gene, set())
            metabolic |= {
                p for p in gene_to_pathways.get(gene, set()) if is_metabolic(p)
            }
        in_kegg.append(bool(genes))
        kegg_ec.append(";".join(sorted(ec_numbers)))
        n_metabolic.append(len(metabolic))

    df = df.copy()
    df["in_kegg"] = in_kegg
    df["kegg_ec"] = kegg_ec
    df["has_kegg_ec"] = df["kegg_ec"] != ""
    df["kegg_metabolic_pathways"] = n_metabolic
    df["kegg_enzyme_evidence"] = df["has_kegg_ec"]
    return df


# ---------------------------------------------------------------------------
# Analyses
# ---------------------------------------------------------------------------
def label_agreement(df):
    """Question 1: agreement between our labels and KEGG enzyme evidence."""
    mapped = df[df["in_kegg"]]
    enzymes = mapped[mapped["label"] == config.LABEL_ENZYME]
    non_enzymes = mapped[mapped["label"] == config.LABEL_NON_ENZYME]

    enz_confirmed = int(enzymes["kegg_enzyme_evidence"].sum())
    non_flagged = int(non_enzymes["kegg_enzyme_evidence"].sum())

    print("\n" + "=" * 72)
    print("QUESTION 1 — DO OUR LABELS AGREE WITH KEGG?")
    print("=" * 72)
    print(f"Proteins in dataset          : {len(df)}")
    print(f"Mapped to a KEGG human gene  : {len(mapped)} "
          f"({len(mapped) / len(df):.1%})")
    print("-" * 72)
    print(f"Our enzymes (mapped)         : {len(enzymes)}")
    print(f"  with KEGG EC number        : {enz_confirmed} "
          f"({_pct(enz_confirmed, len(enzymes))})")
    print(f"Our non-enzymes (mapped)     : {len(non_enzymes)}")
    print(f"  with KEGG EC number        : {non_flagged} "
          f"({_pct(non_flagged, len(non_enzymes))})  <- candidate mislabels")

    # Evidence-class breakdown for enzymes: does KEGG back the GO-only group?
    print("\nKEGG EC support by evidence class (enzymes only):")
    for evidence in [config.EVIDENCE_BOTH, config.EVIDENCE_EC_ONLY,
                     config.EVIDENCE_GO_ONLY]:
        subset = enzymes[enzymes["evidence_class"] == evidence]
        hits = int(subset["kegg_enzyme_evidence"].sum())
        print(f"  {evidence:<12} {hits:>5} / {len(subset):<5} "
              f"({_pct(hits, len(subset))})")

    # Metabolic pathway membership, descriptive only.
    print("\nIn at least one KEGG metabolic pathway:")
    for label_value, name in config.LABEL_NAMES.items():
        subset = mapped[mapped["label"] == label_value]
        hits = int((subset["kegg_metabolic_pathways"] > 0).sum())
        print(f"  {name:<12} {hits:>5} / {len(subset):<5} "
              f"({_pct(hits, len(subset))})")

    go_only = enzymes[enzymes["evidence_class"] == config.EVIDENCE_GO_ONLY]
    return {
        "proteins_total": int(len(df)),
        "proteins_mapped_to_kegg": int(len(mapped)),
        "enzymes_mapped": int(len(enzymes)),
        "enzymes_with_kegg_ec": enz_confirmed,
        "non_enzymes_mapped": int(len(non_enzymes)),
        "non_enzymes_with_kegg_ec": non_flagged,
        "go_only_mapped": int(len(go_only)),
        "go_only_with_kegg_ec": int(go_only["kegg_enzyme_evidence"].sum()),
    }


def false_positive_audit(df):
    """Question 2: are the model's false positives enriched for KEGG enzymes?"""
    if not config.TEST_PREDICTIONS_CSV.exists():
        print("\n(Skipping question 2: run train.py first to create "
              f"{config.TEST_PREDICTIONS_CSV.name}.)")
        return None

    preds = pd.read_csv(config.TEST_PREDICTIONS_CSV)
    preds = preds.merge(
        df[["accession", "in_kegg", "kegg_enzyme_evidence", "kegg_ec"]],
        on="accession", how="left",
    )

    # Only true non-enzymes that KEGG knows about.
    negatives = preds[
        (preds["label"] == config.LABEL_NON_ENZYME) & (preds["in_kegg"] == True)
    ]
    false_pos = negatives[negatives["predicted_label"] == config.LABEL_ENZYME]
    true_neg = negatives[negatives["predicted_label"] == config.LABEL_NON_ENZYME]

    fp_hits = int(false_pos["kegg_enzyme_evidence"].sum())
    tn_hits = int(true_neg["kegg_enzyme_evidence"].sum())

    # 2x2 table: rows = model call, columns = KEGG says enzyme / not.
    table = [
        [fp_hits, len(false_pos) - fp_hits],
        [tn_hits, len(true_neg) - tn_hits],
    ]
    odds_ratio, p_value = fisher_exact(table, alternative="greater")

    print("\n" + "=" * 72)
    print("QUESTION 2 — ARE THE MODEL'S FALSE POSITIVES REALLY ERRORS?")
    print("=" * 72)
    print("Among test-set proteins labelled non-enzyme and mapped to KEGG:")
    print(f"  Model said ENZYME     (false positives) : "
          f"{fp_hits:>4} / {len(false_pos):<4} have KEGG EC "
          f"({_pct(fp_hits, len(false_pos))})")
    print(f"  Model said NON-ENZYME (true negatives)  : "
          f"{tn_hits:>4} / {len(true_neg):<4} have KEGG EC "
          f"({_pct(tn_hits, len(true_neg))})")
    print("-" * 72)
    print(f"Fisher's exact test (one-sided): odds ratio = {odds_ratio:.2f}, "
          f"p = {p_value:.2e}")

    if p_value < 0.05 and odds_ratio > 1:
        print("\nInterpretation: KEGG enzyme evidence is significantly more")
        print("common among the model's false positives. Part of the apparent")
        print("error rate is label noise: the model is flagging proteins that")
        print("an independent database also considers enzymes.")
    else:
        print("\nInterpretation: no significant enrichment. The false positives")
        print("look like ordinary model errors rather than hidden enzymes.")

    # Highest-confidence candidates, for manual inspection.
    candidates = false_pos[false_pos["kegg_enzyme_evidence"] == True]
    candidates = candidates.sort_values("enzyme_probability", ascending=False)
    candidates[["accession", "enzyme_probability", "kegg_ec"]].to_csv(
        config.KEGG_CANDIDATES_CSV, index=False
    )
    if len(candidates):
        print(f"\nTop candidates (model-confident, KEGG-supported):")
        for row in candidates.head(10).itertuples():
            print(f"  {row.accession:<12} p(enzyme)={row.enzyme_probability:.3f}"
                  f"  KEGG EC {row.kegg_ec}")
        print(f"Full list -> {config.KEGG_CANDIDATES_CSV}")
        print("Check a few on uniprot.org before claiming anything about them.")

    return {
        "false_positives_mapped": int(len(false_pos)),
        "false_positives_with_kegg_ec": fp_hits,
        "true_negatives_mapped": int(len(true_neg)),
        "true_negatives_with_kegg_ec": tn_hits,
        "fisher_odds_ratio": float(odds_ratio),
        "fisher_p_value": float(p_value),
    }


def _pct(part, whole):
    return f"{part / whole:.1%}" if whole else "n/a"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if not config.PROCESSED_CSV.exists():
        print(f"Processed file not found: {config.PROCESSED_CSV}")
        print("Run: python training/data_preprocessing.py")
        sys.exit(1)

    print("=" * 72)
    print("KEGG CROSS-DATABASE VALIDATION")
    print("=" * 72)
    org = config.KEGG_ORGANISM
    print("Downloading mappings (cached after the first successful run):")
    uniprot_text = fetch_uniprot_kegg_xrefs()
    ec_text = fetch_kegg_table(f"link/enzyme/{org}", config.KEGG_GENE_EC)
    pathway_text = fetch_kegg_table(f"link/pathway/{org}", config.KEGG_GENE_PATHWAY)

    uniprot_to_genes = build_uniprot_to_genes(uniprot_text)
    gene_to_ec = build_gene_to_values(ec_text, "ec:")
    gene_to_pathways = build_gene_to_values(pathway_text, "path:")

    check_table(uniprot_to_genes, config.UNIPROT_KEGG_XREF,
                "P00918<TAB>hsa:760;", config.MIN_EXPECTED_UNIPROT_LINKS)
    check_table(gene_to_ec, config.KEGG_GENE_EC,
                "hsa:760<TAB>ec:4.2.1.1", config.MIN_EXPECTED_EC_GENES)
    check_table(gene_to_pathways, config.KEGG_GENE_PATHWAY,
                "hsa:760<TAB>path:hsa00910", config.MIN_EXPECTED_PATHWAY_GENES)
    print(f"\nUniProt entries linked to KEGG        : {len(uniprot_to_genes)}")
    print(f"KEGG human genes with an EC number    : {len(gene_to_ec)}")
    print(f"KEGG human genes in any pathway       : {len(gene_to_pathways)}")

    df = pd.read_csv(config.PROCESSED_CSV)
    df = annotate_with_kegg(df, uniprot_to_genes, gene_to_ec, gene_to_pathways)

    report = {"label_agreement": label_agreement(df)}
    fp_report = false_positive_audit(df)
    if fp_report:
        report["false_positive_audit"] = fp_report

    with open(config.KEGG_REPORT_JSON, "w") as handle:
        json.dump(report, handle, indent=2)
    print(f"\nSaved -> {config.KEGG_REPORT_JSON}")


if __name__ == "__main__":
    main()
