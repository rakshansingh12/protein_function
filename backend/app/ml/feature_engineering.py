"""
Feature extraction: amino acid sequence -> 29 numeric features.

THIS FILE IS THE SINGLE SOURCE OF TRUTH.

Both the training pipeline (training/feature_engineering.py) and the FastAPI
backend import from here. If training and inference used two separate
implementations, any small difference (a reordered column, a different unit)
would silently corrupt every prediction. One module removes that whole class
of bug.

Feature layout (order is fixed and must never change):
    [0:20]  amino acid composition, fractions, alphabetical A..Y
    [20]    sequence length
    [21]    molecular weight (Da)
    [22]    aromaticity
    [23]    instability index
    [24]    isoelectric point (pI)
    [25]    GRAVY (grand average of hydropathy)
    [26]    helix fraction
    [27]    turn fraction
    [28]    sheet fraction
"""

from Bio.SeqUtils.ProtParam import ProteinAnalysis

# The 20 standard amino acids in fixed alphabetical order.
STANDARD_AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"

# Residues ProtParam cannot handle: X (any), B (D/N), Z (E/Q), J (I/L),
# U (selenocysteine), O (pyrrolysine). Molecular weight and hydropathy are
# undefined for these, so sequences containing them are rejected upstream.
NON_STANDARD_RESIDUES = "XBZJUO"

# Ordered feature names. Used for the comparison table, feature importances,
# and metadata.json.
FEATURE_NAMES = (
    [f"aa_{aa}" for aa in STANDARD_AMINO_ACIDS]
    + [
        "sequence_length",
        "molecular_weight",
        "aromaticity",
        "instability_index",
        "isoelectric_point",
        "gravy",
        "helix_fraction",
        "turn_fraction",
        "sheet_fraction",
    ]
)

N_FEATURES = len(FEATURE_NAMES)  # 29

# Subset used by the physicochemical comparison dashboard (Addition #2).
COMPARISON_PROPERTIES = [
    "isoelectric_point",
    "gravy",
    "molecular_weight",
    "aromaticity",
    "instability_index",
]


def clean_sequence(sequence):
    """
    Normalise a raw sequence string: strip whitespace, drop FASTA header lines,
    uppercase.

    Users paste sequences with newlines, numbering, or a leading '>' header.
    This makes all of those work without special-casing them elsewhere.
    """
    if sequence is None:
        return ""

    lines = []
    for line in str(sequence).splitlines():
        line = line.strip()
        if line.startswith(">"):  # FASTA header, ignore
            continue
        lines.append(line)

    joined = "".join(lines)
    # Remove anything that is not a letter (digits from numbered sequences,
    # spaces, asterisks marking stop codons).
    return "".join(ch for ch in joined.upper() if ch.isalpha())


def validate_sequence(sequence, min_length=50, max_length=2000):
    """
    Check that a cleaned sequence can actually be featurised.

    Returns (is_valid, error_message). error_message is None when valid.

    Kept as a plain function returning a tuple rather than raising, because the
    API layer needs to turn failures into readable HTTP 400 messages and the
    training loop needs to silently skip bad rows.
    """
    if not sequence:
        return False, "Sequence is empty."

    if len(sequence) < min_length:
        return False, (
            f"Sequence is too short ({len(sequence)} residues). "
            f"Minimum is {min_length}; physicochemical estimates are unstable "
            f"on very short fragments."
        )

    if len(sequence) > max_length:
        return False, (
            f"Sequence is too long ({len(sequence)} residues). "
            f"Maximum is {max_length}."
        )

    invalid = sorted(set(sequence) - set(STANDARD_AMINO_ACIDS))
    if invalid:
        return False, (
            f"Sequence contains non-standard residues: {', '.join(invalid)}. "
            f"Only the 20 standard amino acids are supported, because "
            f"molecular weight and hydropathy are undefined for ambiguous codes."
        )

    return True, None


def calculate_features(sequence):
    """
    Compute the 29 physicochemical features for one cleaned, validated sequence.

    Returns a list of 29 floats in FEATURE_NAMES order.

    Biological reasoning for the feature set:
      - Amino acid composition (20): enzymes are enriched in catalytic residues
        such as His, Cys, Asp, Glu and Ser, so raw composition already carries
        functional signal.
      - Length / molecular weight: enzymes tend to need a folded catalytic
        domain, which puts a floor on their size.
      - Aromaticity: aromatic residues are common in substrate-binding pockets.
      - Instability index: an in-vitro stability estimate from dipeptide
        composition (Guruprasad et al.).
      - Isoelectric point: catalytic sites often depend on charged residues, so
        net-charge behaviour differs between functional classes.
      - GRAVY: hydropathy separates soluble globular enzymes from hydrophobic
        membrane and structural proteins.
      - Helix / turn / sheet fractions: a coarse secondary-structure profile
        from residue propensities.
    """
    analysis = ProteinAnalysis(sequence)

    # 1-20: composition as fractions (sum to 1.0), fixed alphabetical order.
    #
    # We divide raw residue counts by length ourselves instead of calling
    # ProtParam's percentage helper. Reason: BioPython renamed that helper
    # (get_amino_acids_percent() -> amino_acids_percent) AND changed its scale
    # from fractions to percentages between releases. Computing it here means
    # the feature values are identical on every BioPython version, so a model
    # trained on one machine stays valid on another.
    counts = analysis.count_amino_acids()
    length = len(sequence)
    features = [float(counts.get(aa, 0)) / length for aa in STANDARD_AMINO_ACIDS]

    # 21-29: global physicochemical descriptors.
    helix, turn, sheet = analysis.secondary_structure_fraction()

    features.extend(
        [
            float(len(sequence)),
            float(analysis.molecular_weight()),
            float(analysis.aromaticity()),
            float(analysis.instability_index()),
            float(analysis.isoelectric_point()),
            float(analysis.gravy()),
            float(helix),
            float(turn),
            float(sheet),
        ]
    )

    # Guard against silent drift if someone edits FEATURE_NAMES later.
    assert len(features) == N_FEATURES, (
        f"Expected {N_FEATURES} features, produced {len(features)}."
    )
    return features


def features_to_dict(features):
    """Pair a feature vector with its names. Used by the API response."""
    return dict(zip(FEATURE_NAMES, features))


def extract_from_raw(raw_sequence, min_length=50, max_length=2000):
    """
    Convenience wrapper: clean -> validate -> featurise.

    Returns (features, cleaned_sequence, error_message).
    On failure, features is None and error_message explains why.
    """
    cleaned = clean_sequence(raw_sequence)
    is_valid, error = validate_sequence(cleaned, min_length, max_length)
    if not is_valid:
        return None, cleaned, error
    return calculate_features(cleaned), cleaned, None
