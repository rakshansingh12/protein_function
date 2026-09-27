from backend.tests.conftest import requires_artefacts


@requires_artefacts
def test_load_artefacts_returns_required_keys():
    from backend.app.ml.model_loader import load_artefacts

    artefacts = load_artefacts()
    for key in ["final_model", "scaler", "training_features", "class_stats",
                "model_results", "metadata"]:
        assert artefacts[key] is not None


@requires_artefacts
def test_model_has_predict_proba():
    from backend.app.ml.model_loader import load_artefacts

    artefacts = load_artefacts()
    assert hasattr(artefacts["final_model"], "predict_proba")
