"""
Known catalytic motif scan: a supplementary, rule-based check alongside the
machine-learning prediction. It never overrides the model's output -- these
are short, low-specificity patterns useful as a talking point, not proof of
function.
"""

import re

DISCLAIMER = (
    "Known catalytic motif scan — supplementary rule-based analysis. "
    "Motif detection does not override the machine-learning prediction."
)

MOTIFS = [
    {
        "name": "Serine protease-related (simplified)",
        # TODO: Replace this simplified pattern with the official PROSITE pattern
        # before production use.
        "regex": r"[DES][ST].[LIVM]",
        "notation": "[DES]-[ST]-x-[LIVM]",
        "explanation": (
            "A simplified approximation of the serine protease active-site "
            "motif. Official PROSITE patterns or ScanProsite should be "
            "preferred: this 4-residue pattern matches most proteins by "
            "chance and has low specificity."
        ),
    },
    {
        "name": "HEXXH zinc-binding",
        "regex": r"HE..H",
        "notation": "H-E-x-x-H",
        "explanation": (
            "A characteristic motif of zinc metalloproteases and other "
            "metalloenzymes; the two histidines coordinate the catalytic "
            "zinc ion."
        ),
    },
    {
        "name": "Walker A / P-loop",
        "regex": r"[AG].{4}GK[ST]",
        "notation": "[AG]-x(4)-G-K-[ST]",
        "explanation": (
            "The phosphate-binding loop found in many ATP/GTP-binding "
            "proteins."
        ),
    },
]


def scan_motifs(sequence):
    """
    Scan a cleaned protein sequence for each known motif.

    Uses non-overlapping matches (re.finditer default) rather than scanning
    every possible start position, so overlapping near-matches of the same
    motif are not double-counted -- consistent with how PROSITE reports
    matches.

    Positions are 1-based and inclusive, matching biological convention.
    """
    matches = []
    not_found = []

    for motif in MOTIFS:
        pattern = re.compile(motif["regex"])
        hits = list(pattern.finditer(sequence))
        if not hits:
            not_found.append(motif["name"])
            continue
        for hit in hits:
            matches.append({
                "name": motif["name"],
                "start": hit.start() + 1,
                "end": hit.end(),
                "match": hit.group(),
                "explanation": motif["explanation"],
            })

    return {
        "matches": matches,
        "not_found": not_found,
        "disclaimer": DISCLAIMER,
    }
