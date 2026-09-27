"""
Look up supplementary database records (UniProt, PDB, AlphaFold, KEGG) for a
protein that exactly matches a known accession. Isolated by design: every
external call is wrapped so a slow or failing third-party service can never
turn into a 5xx for the rest of the API -- a missing source becomes null,
not an error.
"""

import re

import requests

UNIPROT_ACCESSION_RE = re.compile(
    r"^([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})$"
)

UNIPROT_URL = "https://rest.uniprot.org/uniprotkb/{accession}.json"
ALPHAFOLD_URL = "https://alphafold.ebi.ac.uk/api/prediction/{accession}"

_cache = {}


def is_valid_accession(accession):
    return bool(UNIPROT_ACCESSION_RE.match(accession))


def _fetch_uniprot(accession):
    """Recommended name, organism, subcellular locations and PDB cross-refs."""
    try:
        response = requests.get(UNIPROT_URL.format(accession=accession), timeout=(3, 8))
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return None, []

    try:
        protein_name = (
            data.get("proteinDescription", {})
            .get("recommendedName", {})
            .get("fullName", {})
            .get("value")
        )
        organism = data.get("organism", {}).get("scientificName")

        locations = []
        for comment in data.get("comments", []):
            if comment.get("commentType") != "SUBCELLULAR LOCATION":
                continue
            for entry in comment.get("subcellularLocations", []):
                value = entry.get("location", {}).get("value")
                if value:
                    locations.append(value)

        pdb_ids = []
        for xref in data.get("uniProtKBCrossReferences", []):
            if xref.get("database") != "PDB":
                continue
            properties = {p["key"]: p["value"] for p in xref.get("properties", [])}
            pdb_ids.append({
                "id": xref["id"],
                "method": properties.get("Method"),
                "resolution": properties.get("Resolution"),
                "chains": properties.get("Chains"),
                "url": f"https://www.rcsb.org/structure/{xref['id']}",
            })

        uniprot_result = {
            "protein_name": protein_name,
            "organism": organism,
            "subcellular_locations": locations,
        }
        return uniprot_result, pdb_ids
    except (KeyError, TypeError, AttributeError):
        return None, []


def _fetch_alphafold(accession):
    """Mean pLDDT and fraction very-low-confidence residues, from AlphaFold DB."""
    try:
        response = requests.get(ALPHAFOLD_URL.format(accession=accession), timeout=(3, 8))
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return None

    try:
        if not data:
            return None
        entry = next((e for e in data if str(e.get("entryId", "")).endswith("-F1")), data[0])
        return {
            "entry_id": entry["entryId"],
            "mean_plddt": entry["globalMetricValue"],
            "fraction_plddt_very_low": entry["fractionPlddtVeryLow"],
            "url": f"https://alphafold.ebi.ac.uk/entry/{accession}",
        }
    except (KeyError, TypeError, IndexError):
        return None


def _fetch_kegg(accession, kegg_pathways):
    """KEGG genes and pathways, from the precomputed map only (no live call)."""
    if not kegg_pathways:
        return None
    record = kegg_pathways.get(accession)
    if not record:
        return None

    pathways = [
        {
            "id": p["id"],
            "name": p["name"],
            "url": f"https://www.kegg.jp/pathway/{p['id']}",
        }
        for p in record.get("pathways", [])
    ]
    genes = [
        {"gene": gene, "url": f"https://www.kegg.jp/entry/{gene}"}
        for gene in record.get("kegg_genes", [])
    ]
    if not genes and not pathways and not record.get("ec"):
        return None
    return {"genes": genes, "ec": record.get("ec", []), "pathways": pathways}


def enrich(accession, kegg_pathways):
    """
    Fetch all four sources for one accession, using an in-memory cache so a
    repeated lookup in the same process does not re-hit external services.
    """
    if accession in _cache:
        return _cache[accession]

    uniprot, pdb = _fetch_uniprot(accession)
    alphafold = _fetch_alphafold(accession)
    kegg = _fetch_kegg(accession, kegg_pathways)

    result = {
        "uniprot": uniprot,
        "pdb": pdb if pdb else None,
        "alphafold": alphafold,
        "kegg": kegg,
    }
    if not any([uniprot, pdb, alphafold, kegg]):
        result["message"] = "No additional database records found."

    _cache[accession] = result
    return result
