from backend.app.services.motif_service import MOTIFS, scan_motifs

# Padding keeps matches away from position 1 so start/end assertions are
# unambiguous, and avoids accidentally forming a second, unrelated motif.
HEXXH_SEQUENCE = "AAAA" + "HEGGH" + "A" * 20
WALKER_A_SEQUENCE = "AAAA" + "AAAAAGKS" + "A" * 20


def test_hexxh_found_at_correct_position():
    result = scan_motifs(HEXXH_SEQUENCE)
    names = [m["name"] for m in result["matches"]]
    assert "HEXXH zinc-binding" in names
    match = next(m for m in result["matches"] if m["name"] == "HEXXH zinc-binding")
    # 1-based inclusive: "HEGGH" starts right after the 4-residue prefix.
    assert match["start"] == 5
    assert match["end"] == 9
    assert match["match"] == "HEGGH"


def test_walker_a_found_at_correct_position():
    result = scan_motifs(WALKER_A_SEQUENCE)
    match = next(m for m in result["matches"] if m["name"] == "Walker A / P-loop")
    assert match["start"] == 5
    assert match["end"] == 12
    assert match["match"] == "AAAAAGKS"


def test_absent_motifs_listed_in_not_found():
    result = scan_motifs(HEXXH_SEQUENCE)
    found_names = {m["name"] for m in result["matches"]}
    for motif in MOTIFS:
        if motif["name"] not in found_names:
            assert motif["name"] in result["not_found"]


def test_disclaimer_present():
    result = scan_motifs(HEXXH_SEQUENCE)
    assert "does not override" in result["disclaimer"].lower()
