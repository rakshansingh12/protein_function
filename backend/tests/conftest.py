"""Shared pytest setup: project root on sys.path, skip when artefacts are missing."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.ml.model_loader import REQUIRED_FILES  # noqa: E402

ARTEFACTS_PRESENT = all(path.exists() for path in REQUIRED_FILES.values())

requires_artefacts = pytest.mark.skipif(
    not ARTEFACTS_PRESENT, reason="model artefacts are missing"
)
