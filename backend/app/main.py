"""
FastAPI app entry point. Loads model artefacts at startup (a warning, not a
crash, if they are missing -- /api/health and routes then report the
problem instead of the process refusing to start), then serves the API
first and the static frontend second, so both share one origin and the UI
can call /api/... with relative URLs.

The frontend is a Next.js app in frontend/; `npm run build` there writes a
static export to frontend/out/, which is what gets served here.

Run from the project root:  uvicorn backend.app.main:app --reload
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import router
from backend.app.ml.model_loader import ArtefactsMissingError, load_artefacts

logger = logging.getLogger(__name__)

app = FastAPI(title="Protein Function Classifier")


@app.on_event("startup")
def _load_artefacts_at_startup():
    try:
        load_artefacts()
    except ArtefactsMissingError as exc:
        logger.warning("Model artefacts missing at startup: %s", exc)


app.include_router(router)

FRONTEND_BUILD_DIR = Path(__file__).resolve().parents[2] / "frontend" / "out"
if FRONTEND_BUILD_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIR, html=True), name="frontend")
else:
    # API still works; only the UI is missing until the frontend is built.
    logger.warning(
        "Frontend build not found at %s -- run `npm run build` in frontend/.",
        FRONTEND_BUILD_DIR,
    )
