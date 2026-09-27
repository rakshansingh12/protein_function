"""
API routes (prefix /api). Thin: parse the request, call a service, shape the
response. All real work happens in backend/app/services and backend/app/ml.
"""

from fastapi import APIRouter, HTTPException

from backend.app.api.schemas import HealthResponse, PredictRequest
from backend.app.ml.model_loader import ArtefactsMissingError, load_artefacts
from backend.app.services.enrichment_service import enrich, is_valid_accession
from backend.app.services.prediction_service import predict

router = APIRouter(prefix="/api")


def _artefacts_or_503():
    try:
        return load_artefacts()
    except ArtefactsMissingError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/health", response_model=HealthResponse)
def health():
    try:
        load_artefacts()
        model_loaded = True
    except ArtefactsMissingError:
        model_loaded = False
    return {"status": "ok", "model_loaded": model_loaded}


@router.get("/model-info")
def model_info():
    artefacts = _artefacts_or_503()
    model_results = artefacts["model_results"]
    random_split = artefacts.get("model_results_random_split")
    metadata = artefacts["metadata"]

    models = {}
    for name, result in model_results["models"].items():
        test = result["test"]
        entry = {
            "roc_auc": test["roc_auc"],
            "f1": test["f1"],
            "accuracy": test["accuracy"],
            "precision": test["precision"],
            "recall": test["recall"],
        }
        if random_split and name in random_split["models"]:
            entry["random_split_roc_auc"] = random_split["models"][name]["test"]["roc_auc"]
        models[name] = entry

    return {
        "best_model": model_results["best_model"],
        "split_mode": model_results.get("split_mode"),
        "selection_rule": model_results["selection_rule"],
        "ensemble_selected": model_results["ensemble_selected"],
        "training_dataset_size": metadata["training_dataset_size"],
        "class_counts": metadata["class_counts"],
        "models": models,
        "size_baseline": {
            "test_roc_auc": model_results["size_baseline"]["test"]["roc_auc"],
            "lift_of_full_model": model_results["size_baseline"]["lift_of_full_model"],
        },
    }


@router.post("/predict")
def predict_route(body: PredictRequest):
    artefacts = _artefacts_or_503()
    try:
        return predict(body.sequence, artefacts)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/enrich/{accession}")
def enrich_route(accession: str):
    if not is_valid_accession(accession):
        raise HTTPException(status_code=400, detail="Malformed UniProt accession.")

    artefacts = _artefacts_or_503()
    sequence_index = artefacts.get("sequence_index")
    known_accessions = (
        {entry["accession"] for entry in sequence_index.values()} if sequence_index else set()
    )
    if accession not in known_accessions:
        raise HTTPException(
            status_code=404,
            detail="Accession is not in the dataset; enrichment only runs for "
                   "known proteins.",
        )

    return enrich(accession, artefacts.get("kegg_pathways"))
