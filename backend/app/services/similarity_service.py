"""
Find the nearest proteins to a query, by physicochemical features, within
the training split only (the split the scaler and model were fit on -- the
test split must stay unseen).
"""

from sklearn.neighbors import NearestNeighbors

_nn_index = None


def _get_index(training_features):
    """Fit NearestNeighbors once and cache it (module-level, like model_loader)."""
    global _nn_index
    if _nn_index is None:
        _nn_index = NearestNeighbors(n_neighbors=5, metric="euclidean")
        _nn_index.fit(training_features["features_scaled"])
    return _nn_index


def find_similar(features, scaler, training_features):
    """
    Return the 5 nearest training-split proteins to `features` (raw, 29-long).

    similarity = 100 / (1 + distance): a simple, monotonic, explainable score
    on (0, 100] where 100 means identical (scaled) features. Euclidean
    distance in scaled space has no natural upper bound, so a raw distance is
    not intuitive to a viva audience; this transform is.
    """
    index = _get_index(training_features)
    scaled_query = scaler.transform([features])
    distances, indices = index.kneighbors(scaled_query)

    results = []
    for distance, idx in zip(distances[0], indices[0]):
        label = training_features["labels"][idx]
        results.append({
            "accession": training_features["accessions"][idx],
            "class": "enzyme" if label == 1 else "non-enzyme",
            "distance": float(distance),
            "similarity": round(100 / (1 + distance), 1),
        })
    return results
