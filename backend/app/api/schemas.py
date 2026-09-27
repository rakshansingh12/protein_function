"""Pydantic request/response models for the /api routes."""

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    sequence: str = Field(..., max_length=20000)


class HealthResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    status: str
    model_loaded: bool
