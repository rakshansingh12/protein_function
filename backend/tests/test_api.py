import json
from pathlib import Path

import pandas as pd
import pytest
import requests
from fastapi.testclient import TestClient

from backend.tests.conftest import ARTEFACTS_PRESENT, requires_artefacts

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
KNOWN_ACCESSION = "P00918"


@pytest.fixture
def client():
    from backend.app.main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_enrichment_cache():
    from backend.app.services import enrichment_service

    enrichment_service._cache.clear()
    yield
    enrichment_service._cache.clear()


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] == ARTEFACTS_PRESENT


@requires_artefacts
def test_model_info(client):
    response = client.get("/api/model-info")
    assert response.status_code == 200
    body = response.json()
    assert "best_model" in body
    assert "models" in body
    assert body["best_model"] in body["models"]


@requires_artefacts
def test_predict_real_dataset_sequence(client):
    df = pd.read_csv("data/processed/proteins_labeled.csv")
    sequence = df.iloc[0]["sequence"]

    response = client.post("/api/predict", json={"sequence": sequence})
    assert response.status_code == 200
    body = response.json()
    for field in ["prediction", "probability_enzyme", "confidence", "model_name",
                  "sequence_length", "cleaned_sequence", "features", "comparison",
                  "similar_proteins", "motifs", "dataset_match", "notes"]:
        assert field in body
    assert body["prediction"] in ("ENZYME", "NON-ENZYME")


@requires_artefacts
def test_predict_invalid_sequence_returns_400(client):
    response = client.post("/api/predict", json={"sequence": "HELLO"})
    assert response.status_code == 400
    assert "detail" in response.json()


def test_enrich_malformed_accession_returns_400(client):
    response = client.get("/api/enrich/not_an_accession")
    assert response.status_code == 400


@requires_artefacts
def test_enrich_network_failure_returns_200_with_nulls(client, monkeypatch):
    def raise_connection_error(*args, **kwargs):
        raise requests.ConnectionError("simulated network failure")

    monkeypatch.setattr(requests, "get", raise_connection_error)

    response = client.get(f"/api/enrich/{KNOWN_ACCESSION}")
    assert response.status_code == 200
    body = response.json()
    assert body["uniprot"] is None
    assert body["pdb"] is None
    assert body["alphafold"] is None
    # KEGG is read from the precomputed file, not a live call, so it is
    # unaffected by a network failure -- this is not asserted null here.


@requires_artefacts
def test_enrich_parses_saved_fixtures(client, monkeypatch):
    uniprot_fixture = json.loads((FIXTURES_DIR / "uniprot_P00918.json").read_text())
    alphafold_fixture = json.loads((FIXTURES_DIR / "alphafold_P00918.json").read_text())

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload
            self.status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    def fake_get(url, timeout=None):
        if "alphafold" in url:
            return FakeResponse(alphafold_fixture)
        return FakeResponse(uniprot_fixture)

    monkeypatch.setattr(requests, "get", fake_get)

    response = client.get(f"/api/enrich/{KNOWN_ACCESSION}")
    assert response.status_code == 200
    body = response.json()

    assert body["uniprot"]["protein_name"] == "Carbonic anhydrase 2"
    assert body["uniprot"]["organism"] == "Homo sapiens"
    assert body["pdb"][0]["id"] == uniprot_fixture["uniProtKBCrossReferences"][0]["id"]
    assert body["alphafold"]["entry_id"] == alphafold_fixture[0]["entryId"]
