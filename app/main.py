"""Property Value Estimator — facade over the Task 1 model service.

Receives property details, validates them, forwards to the downstream model
service, persists the result, and returns a clean response.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Query, Response

from app import client, config, store
from app.schemas import (
    EstimateListResponse,
    EstimateResponse,
    HouseFeatures,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the DB table and the shared HTTP client on startup; close on shutdown."""
    store.init_db()
    app.state.model_client = httpx.Client(
        base_url=config.MODEL_SERVICE_URL,
        timeout=config.MODEL_SERVICE_TIMEOUT,
    )
    yield
    app.state.model_client.close()


app = FastAPI(title="Property Value Estimator Service", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/estimates", response_model=EstimateResponse, status_code=201)
def create_estimate(payload: HouseFeatures):
    """Validate a single property, predict its price, and persist the result."""
    features = payload.model_dump()
    [prediction] = client.predict(app.state.model_client, [features])
    record = store.save(features, prediction)
    return record


@app.post("/estimates/batch", response_model=EstimateListResponse, status_code=201)
def create_estimate_batch(payload: list[HouseFeatures]):
    """Predict prices for multiple properties in a single round-trip.

    Used by the comparison view. The whole list is validated first; any invalid
    entry fails the request with a 422 before the model is called.
    """
    if not payload:
        raise HTTPException(status_code=422, detail="At least one property is required")
    if len(payload) > config.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=422,
            detail=f"Batch is limited to {config.MAX_BATCH_SIZE} properties",
        )

    features_list = [h.model_dump() for h in payload]
    predictions = client.predict(app.state.model_client, features_list)

    records = store.save_many(list(zip(features_list, predictions)))
    return {"estimates": records}


@app.get("/estimates", response_model=EstimateListResponse)
def list_estimates(limit: int = Query(default=100, ge=1, le=1000)):
    """Return the most recent estimates (history), newest first."""
    return {"estimates": store.list_all(limit=limit)}


@app.get("/estimates/{estimate_id}", response_model=EstimateResponse)
def get_estimate(estimate_id: str):
    record = store.get_one(estimate_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@app.delete("/estimates/{estimate_id}", status_code=204)
def delete_estimate(estimate_id: str):
    if not store.delete_one(estimate_id):
        raise HTTPException(status_code=404, detail="Record not found")
    return Response(status_code=204)
