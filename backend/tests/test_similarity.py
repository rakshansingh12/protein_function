from backend.tests.conftest import requires_artefacts


@requires_artefacts
def test_find_similar_returns_5_sorted_neighbours_with_valid_similarity():
    from backend.app.ml.model_loader import load_artefacts
    from backend.app.services.similarity_service import find_similar

    artefacts = load_artefacts()
    training_features = artefacts["training_features"]
    query_features = list(training_features["features_scaled"][0])
    # find_similar scales its input itself, so give it the raw (unscaled)
    # feature values the scaler would have produced this row from -- using
    # the scaler's inverse keeps this test independent of feature units.
    raw_features = artefacts["scaler"].inverse_transform([query_features])[0]

    results = find_similar(raw_features, artefacts["scaler"], training_features)

    assert len(results) == 5
    distances = [r["distance"] for r in results]
    assert distances == sorted(distances)
    for r in results:
        assert 0 < r["similarity"] <= 100
        assert r["class"] in ("enzyme", "non-enzyme")
