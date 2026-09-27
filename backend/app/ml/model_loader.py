"""
Load every trained artefact once and cache it at module level.

Required artefacts (the API cannot serve predictions without these): the
model, its scaler, the training-split feature matrix, class statistics,
model results and metadata. Optional artefacts (sequence index, KEGG
pathways, motif stats, the earlier random-split results) enrich the response
but their absence should not take the whole API down.
"""

import json
from pathlib import Path

import joblib

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODELS_DIR = PROJECT_ROOT / "models"

REQUIRED_FILES = {
    "final_model": MODELS_DIR / "final_model.joblib",
    "scaler": MODELS_DIR / "scaler.joblib",
    "training_features": MODELS_DIR / "training_features.joblib",
    "class_stats": MODELS_DIR / "class_stats.json",
    "model_results": MODELS_DIR / "model_results.json",
    "metadata": MODELS_DIR / "metadata.json",
}

OPTIONAL_FILES = {
    "model_results_random_split": MODELS_DIR / "model_results_random_split.json",
    "sequence_index": MODELS_DIR / "sequence_index.json",
    "kegg_pathways": MODELS_DIR / "kegg_pathways.json",
    "motif_stats": MODELS_DIR / "motif_stats.json",
}


class ArtefactsMissingError(Exception):
    """Raised when a required artefact file is absent. Routes -> HTTP 503."""

    def __init__(self, missing):
        self.missing = missing
        super().__init__(f"Missing required artefacts: {', '.join(missing)}")


_cache = None


def _load_json(path):
    return json.loads(path.read_text())


def load_artefacts():
    """Load all artefacts once; later calls return the cached dict."""
    global _cache
    if _cache is not None:
        return _cache

    missing = [str(path) for path in REQUIRED_FILES.values() if not path.exists()]
    if missing:
        raise ArtefactsMissingError(missing)

    artefacts = {
        "final_model": joblib.load(REQUIRED_FILES["final_model"]),
        "scaler": joblib.load(REQUIRED_FILES["scaler"]),
        "training_features": joblib.load(REQUIRED_FILES["training_features"]),
        "class_stats": _load_json(REQUIRED_FILES["class_stats"]),
        "model_results": _load_json(REQUIRED_FILES["model_results"]),
        "metadata": _load_json(REQUIRED_FILES["metadata"]),
    }

    for key, path in OPTIONAL_FILES.items():
        artefacts[key] = _load_json(path) if path.exists() else None

    _cache = artefacts
    return _cache
