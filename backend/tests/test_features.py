import pytest

from backend.app.ml.feature_engineering import (
    N_FEATURES,
    STANDARD_AMINO_ACIDS,
    calculate_features,
    clean_sequence,
    extract_from_raw,
    validate_sequence,
)

REAL_SEQUENCE = (
    "MSHHWGYGKHNGPEHWHKDFPIAKGERQSPVDIDTHTAKYDPSLKPLSVSYDQATSLRI"
    "LNNGHAFNVEFDDSQDKAVLKGGPLDGTYRLIQFHFHWGSLDGQGSEHTVDKKKYAAEL"
    "HLVHWNTKYGDFGKAVQQPDGLAVLGIFLKVGSAKPGLQKVVDVLDSIKTKGKSADFTN"
    "FDPRGLLPESLDYWTYPGSLTTPPLLECVTWIVLKEPISVSSEQVLKFRKLNFNGEGEP"
    "EELMVDNWRPAQPLKNRQIKASFK"
)


def test_calculate_features_returns_29_values():
    features = calculate_features(REAL_SEQUENCE)
    assert len(features) == N_FEATURES == 29


def test_amino_acid_composition_sums_to_one():
    features = calculate_features(REAL_SEQUENCE)
    composition = features[:20]
    assert sum(composition) == pytest.approx(1.0, abs=1e-6)


def test_clean_sequence_strips_fasta_header_and_newlines():
    raw = ">sp|P00000|TEST some description\nMSHH\nWGYG\n"
    assert clean_sequence(raw) == "MSHHWGYG"


def test_clean_sequence_removes_digits_and_whitespace():
    raw = "1 MSHH 10\n  WGYG 20"
    assert clean_sequence(raw) == "MSHHWGYG"


def test_validate_sequence_rejects_empty():
    is_valid, error = validate_sequence("")
    assert not is_valid
    assert "empty" in error.lower()


def test_validate_sequence_rejects_short():
    is_valid, error = validate_sequence("A" * 10)
    assert not is_valid
    assert "short" in error.lower()


def test_validate_sequence_rejects_non_standard_residues():
    sequence = "X" * 60
    is_valid, error = validate_sequence(sequence)
    assert not is_valid
    assert "non-standard" in error.lower()


def test_validate_sequence_accepts_standard_residues_only():
    sequence = "".join(STANDARD_AMINO_ACIDS[i % 20] for i in range(60))
    is_valid, error = validate_sequence(sequence)
    assert is_valid
    assert error is None


def test_extract_from_raw_round_trip():
    features, cleaned, error = extract_from_raw(f">header\n{REAL_SEQUENCE}")
    assert error is None
    assert cleaned == REAL_SEQUENCE
    assert len(features) == 29
