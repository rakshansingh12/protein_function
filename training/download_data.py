"""
Step 1 of the pipeline: download raw protein data from the UniProt REST API.

WHY THREE SEPARATE QUERIES
--------------------------
The consensus label needs two independent catalytic-evidence sources:

    1. an EC (Enzyme Commission) number
    2. GO:0003824 "catalytic activity" (or any descendant term)

We cannot resolve source 2 by string-matching "GO:0003824" in each entry,
because UniProt entries carry *specific* GO terms (GO:0004252 serine-type
endopeptidase activity, GO:0016301 kinase activity, ...) rather than the root
term. The UniProt search index, however, expands the GO ontology graph: the
query `go:0003824` returns every entry annotated with any descendant of
catalytic activity.

So we ask UniProt three questions and do set arithmetic on the accessions:

    EC  = { accessions matching ec:* }
    GO  = { accessions matching go:0003824 }
    NEG = { accessions matching NOT ec:* AND NOT go:0003824 }

    enzymes      = EC union GO
    EC-only      = EC minus GO
    GO-only      = GO minus EC
    both         = EC intersect GO
    non-enzymes  = NEG

This is the core data-curation contribution of the project: a protein with no
EC number is NOT automatically a non-enzyme. It is only a non-enzyme if both
independent sources are silent.

Run:  python training/download_data.py
"""

import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


def build_base_filter():
    """
    The organism / review-status filter shared by all three queries.

    Keeping this identical across queries is essential: if the negative query
    used a different organism scope than the positive queries, the class
    comparison would be confounded.
    """
    parts = []
    if config.REVIEWED_ONLY:
        parts.append("(reviewed:true)")
    if config.ORGANISM_ID:
        parts.append(f"(organism_id:{config.ORGANISM_ID})")
    # Exclude sequence fragments: a fragment's composition is not representative
    # of the whole protein.
    parts.append("(fragment:false)")
    return " AND ".join(parts)


def uniprot_search(query, max_records=None):
    """
    Run a paginated UniProt search and return a list of entry dicts.

    UniProt uses cursor pagination: each response carries a Link header with
    rel="next". requests exposes that as response.links["next"]["url"], so we
    just follow it until it disappears or we have enough records.
    """
    params = {
        "query": query,
        "fields": config.UNIPROT_FIELDS,
        "format": "json",
        "size": config.UNIPROT_PAGE_SIZE,
    }

    url = config.UNIPROT_SEARCH_URL
    collected = []
    page = 0

    while url:
        response = _get_with_retry(url, params=params if page == 0 else None)
        if response is None:
            print("  ! Giving up on this query after repeated failures.")
            break

        payload = response.json()
        results = payload.get("results", [])
        collected.extend(results)
        page += 1
        print(f"  page {page:>3}  (+{len(results):>3})  total={len(collected)}")

        if max_records is not None and len(collected) >= max_records:
            collected = collected[:max_records]
            break

        # Follow the cursor. params are already baked into the next URL.
        next_link = response.links.get("next", {})
        url = next_link.get("url")

        # Be polite to a public API.
        time.sleep(0.2)

    return collected


def _get_with_retry(url, params=None):
    """GET with a small retry loop. UniProt occasionally returns 5xx."""
    for attempt in range(1, config.UNIPROT_MAX_RETRIES + 1):
        try:
            response = requests.get(
                url, params=params, timeout=config.UNIPROT_TIMEOUT
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            print(f"  ! attempt {attempt}/{config.UNIPROT_MAX_RETRIES}: {exc}")
            if attempt < config.UNIPROT_MAX_RETRIES:
                time.sleep(config.UNIPROT_RETRY_SLEEP)
    return None


def parse_entry(entry):
    """
    Flatten one UniProt JSON entry into the columns we care about.

    UniProt's JSON is deeply nested, so this function is deliberately explicit
    about where each value comes from rather than using a generic walker.
    """
    accession = entry.get("primaryAccession", "")

    # Protein name: recommended name if present, otherwise the first submitted
    # name, otherwise blank.
    protein_desc = entry.get("proteinDescription", {})
    recommended = protein_desc.get("recommendedName", {})
    protein_name = recommended.get("fullName", {}).get("value", "")
    if not protein_name:
        submitted = protein_desc.get("submissionNames", [])
        if submitted:
            protein_name = submitted[0].get("fullName", {}).get("value", "")

    organism = entry.get("organism", {}).get("scientificName", "")
    sequence = entry.get("sequence", {}).get("value", "")

    # EC numbers can be attached to the recommended name and/or to individual
    # domains, so collect from both places.
    ec_numbers = []
    for ec in recommended.get("ecNumbers", []):
        ec_numbers.append(ec.get("value", ""))
    for contained in protein_desc.get("contains", []):
        for ec in contained.get("recommendedName", {}).get("ecNumbers", []):
            ec_numbers.append(ec.get("value", ""))
    ec_numbers = sorted({e for e in ec_numbers if e})

    # Literal GO IDs on the entry. Stored for transparency and manual auditing.
    # NOTE: membership in the catalytic set is decided by the UniProt query,
    # not by searching this list for GO:0003824.
    go_ids = []
    for ref in entry.get("uniProtKBCrossReferences", []):
        if ref.get("database") == "GO":
            go_ids.append(ref.get("id", ""))
    go_ids = sorted({g for g in go_ids if g})

    return {
        "accession": accession,
        "protein_name": protein_name,
        "organism": organism,
        "sequence": sequence,
        "length": len(sequence),
        "ec_numbers": ";".join(ec_numbers),
        "go_ids": ";".join(go_ids),
    }


def entries_to_dataframe(entries):
    """Convert raw UniProt entries into a tidy DataFrame."""
    rows = [parse_entry(e) for e in entries]
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df[df["sequence"].str.len() > 0]
    return df


def run_sanity_check(base_filter):
    """
    Optional external check on our negatives.

    We query families that are documented as non-catalytic (transport,
    structural, immunoglobulin). These labels are NOT used for training. We
    only report how many of them land in our negative set. A high overlap is
    evidence that "no EC and no catalytic GO" is picking up genuinely
    non-catalytic proteins rather than under-annotated enzymes.
    """
    frames = []
    for family, clause in config.NON_CATALYTIC_SANITY_QUERIES.items():
        query = f"{base_filter} AND ({clause})"
        print(f"\n[sanity] {family}: {query}")
        entries = uniprot_search(query, max_records=1000)
        df = entries_to_dataframe(entries)
        if not df.empty:
            df["sanity_family"] = family
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    # A protein can hit more than one family query; keep the first.
    return combined.drop_duplicates(subset="accession", keep="first")


def main():
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    base_filter = build_base_filter()

    print("=" * 72)
    print("UNIPROT DOWNLOAD — CONSENSUS LABELING SOURCES")
    print("=" * 72)
    print(f"Base filter: {base_filter}")
    cap = config.DOWNLOAD_MAX_PER_QUERY
    print(f"Download cap per query: {cap if cap else 'none (complete sets)'}")
    if cap is not None:
        print("  ! WARNING: a download cap truncates the EC/GO/negative sets, so")
        print("  ! the set arithmetic below will misreport EC-only and GO-only.")
        print("  ! Use a cap only for smoke tests, never for reported results.")

    # --- Source 1: proteins with an EC number ------------------------------
    ec_query = f"{base_filter} AND (ec:*)"
    print(f"\n[1/3] EC-annotated proteins\n      {ec_query}")
    ec_df = entries_to_dataframe(
        uniprot_search(ec_query, config.DOWNLOAD_MAX_PER_QUERY)
    )
    ec_df.to_csv(config.RAW_EC_CSV, index=False)
    print(f"      -> {len(ec_df)} entries  ({config.RAW_EC_CSV.name})")

    # --- Source 2: proteins with catalytic activity GO ---------------------
    # `go:0003824` matches the root term AND all its descendants, because the
    # UniProt index expands the GO graph. This is the whole reason we query
    # instead of string-matching.
    go_query = f"{base_filter} AND (go:{config.CATALYTIC_GO_QUERY_ID})"
    print(f"\n[2/3] GO catalytic-activity proteins\n      {go_query}")
    go_df = entries_to_dataframe(
        uniprot_search(go_query, config.DOWNLOAD_MAX_PER_QUERY)
    )
    go_df.to_csv(config.RAW_GO_CSV, index=False)
    print(f"      -> {len(go_df)} entries  ({config.RAW_GO_CSV.name})")

    # --- Source 3: neither EC nor catalytic GO -----------------------------
    neg_query = (
        f"{base_filter} AND NOT (ec:*) "
        f"AND NOT (go:{config.CATALYTIC_GO_QUERY_ID})"
    )
    print(f"\n[3/3] Candidate non-enzymes\n      {neg_query}")
    neg_df = entries_to_dataframe(
        uniprot_search(neg_query, config.DOWNLOAD_MAX_PER_QUERY)
    )
    neg_df.to_csv(config.RAW_NONENZYME_CSV, index=False)
    print(f"      -> {len(neg_df)} entries  ({config.RAW_NONENZYME_CSV.name})")

    # --- Set arithmetic: assign evidence class -----------------------------
    ec_accessions = set(ec_df["accession"])
    go_accessions = set(go_df["accession"])

    positives = pd.concat([ec_df, go_df], ignore_index=True)
    positives = positives.drop_duplicates(subset="accession", keep="first")

    positives["has_ec"] = positives["accession"].isin(ec_accessions)
    positives["has_go_catalytic"] = positives["accession"].isin(go_accessions)

    def evidence_class(row):
        if row["has_ec"] and row["has_go_catalytic"]:
            return config.EVIDENCE_BOTH
        if row["has_ec"]:
            return config.EVIDENCE_EC_ONLY
        return config.EVIDENCE_GO_ONLY

    positives["evidence_class"] = positives.apply(evidence_class, axis=1)
    positives["label"] = config.LABEL_ENZYME

    negatives = neg_df.copy()
    negatives["has_ec"] = False
    negatives["has_go_catalytic"] = False
    negatives["evidence_class"] = config.EVIDENCE_NEITHER
    negatives["label"] = config.LABEL_NON_ENZYME

    combined = pd.concat([positives, negatives], ignore_index=True)

    # A protein should never appear as both positive and negative — the queries
    # are mutually exclusive by construction — but check rather than assume.
    overlap = set(positives["accession"]) & set(negatives["accession"])
    if overlap:
        print(f"\n! WARNING: {len(overlap)} accessions in both sets; dropping "
              f"them from the negatives as catalytic evidence wins.")
        combined = combined[
            ~(
                (combined["label"] == config.LABEL_NON_ENZYME)
                & (combined["accession"].isin(overlap))
            )
        ]

    combined = combined.drop_duplicates(subset="accession", keep="first")
    combined.to_csv(config.RAW_COMBINED_CSV, index=False)

    # --- Optional sanity check --------------------------------------------
    sanity_df = run_sanity_check(base_filter)
    if not sanity_df.empty:
        sanity_df.to_csv(config.RAW_SANITY_CSV, index=False)
        negative_accessions = set(negatives["accession"])
        hits = sanity_df["accession"].isin(negative_accessions).sum()
        print(
            f"\n[sanity] {hits}/{len(sanity_df)} known non-catalytic-family "
            f"proteins fall inside our negative set."
        )

    # --- Summary -----------------------------------------------------------
    print("\n" + "=" * 72)
    print("DOWNLOAD SUMMARY")
    print("=" * 72)
    print(f"EC set                : {len(ec_accessions)}")
    print(f"GO catalytic set      : {len(go_accessions)}")
    print(f"EC only               : {len(ec_accessions - go_accessions)}")
    print(f"GO only               : {len(go_accessions - ec_accessions)}")
    print(f"Both EC and GO        : {len(ec_accessions & go_accessions)}")
    print(f"Neither (non-enzyme)  : {len(negatives)}")
    print(f"Combined raw rows     : {len(combined)}")
    print(f"\nSaved -> {config.RAW_COMBINED_CSV}")
    print("Next: python training/data_preprocessing.py")


if __name__ == "__main__":
    main()