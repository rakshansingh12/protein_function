"""
Thin orchestrator: raw sequence in, full prediction response out. Each piece
of real work (feature extraction, the model, similarity search, motif
scanning, dataset lookup) lives in its own module; this just calls them in
order and assembles the result.
"""

import hashlib

from backend.app.ml.feature_engineering import (
    COMPARISON_PROPERTIES,
    FEATURE_NAMES,
    extract_from_raw,
    features_to_dict,
)
from backend.app.services.motif_service import scan_motifs
from backend.app.services.similarity_service import find_similar


def _dataset_match(cleaned_sequence, sequence_index, training_features):
    if not sequence_index:
        return None
    digest = hashlib.sha256(cleaned_sequence.encode("utf-8")).hexdigest()
    entry = sequence_index.get(digest)
    if entry is None:
        return None
    return {
        **entry,
        "in_training_split": entry["accession"] in training_features["accessions"],
    }


def _comparison_rows(feature_values, class_stats):
    rows = []
    for prop in COMPARISON_PROPERTIES:
        idx = FEATURE_NAMES.index(prop)
        rows.append({
            "property": prop,
            "input": feature_values[idx],
            "enzyme_mean": class_stats["enzyme"][prop]["mean"],
            "enzyme_std": class_stats["enzyme"][prop]["std"],
            "non_enzyme_mean": class_stats["non_enzyme"][prop]["mean"],
            "non_enzyme_std": class_stats["non_enzyme"][prop]["std"],
        })
    return rows


def predict(raw_sequence, artefacts):
    features, cleaned_sequence, error = extract_from_raw(raw_sequence)
    if features is None:
        raise ValueError(error)

    model = artefacts["final_model"]
    probability_enzyme = float(model.predict_proba([features])[0][1])
    label = "ENZYME" if probability_enzyme >= 0.5 else "NON-ENZYME"
    confidence = probability_enzyme if label == "ENZYME" else 1 - probability_enzyme

    similar_proteins = find_similar(
        features, artefacts["scaler"], artefacts["training_features"]
    )

    motif_result = scan_motifs(cleaned_sequence)
    motif_stats = artefacts.get("motif_stats")
    if motif_stats:
        for match in motif_result["matches"]:
            stat = motif_stats.get(match["name"])
            if stat:
                match["class_rates"] = stat

    comparison = _comparison_rows(features, artefacts["class_stats"])

    dataset_match = _dataset_match(
        cleaned_sequence, artefacts.get("sequence_index"), artefacts["training_features"]
    )

    best_model_name = artefacts["model_results"]["best_model"]
    homology_roc_auc = (
        artefacts["model_results"]["models"][best_model_name]["test"]["roc_auc"]
    )

    notes = [
        "The model was trained on reviewed human proteins only.",
        f"Headline homology-aware ROC-AUC for {best_model_name}: "
        f"{homology_roc_auc:.4f}.",
    ]
    if dataset_match and dataset_match["in_training_split"]:
        notes.append(
            "This protein was in the model's training split, so this result "
            "is not an independent test."
        )

    return {
        "prediction": label,
        "probability_enzyme": probability_enzyme,
        "confidence": confidence,
        "model_name": best_model_name,
        "sequence_length": len(cleaned_sequence),
        "cleaned_sequence": cleaned_sequence,
        "features": features_to_dict(features),
        "comparison": comparison,
        "similar_proteins": similar_proteins,
        "motifs": motif_result,
        "dataset_match": dataset_match,
        "notes": notes,
    }
