"""HTTP client for the downstream model service (Task 1)."""
from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def predict(client: httpx.Client, features: list[dict]) -> list[float]:
    """Predict prices for one or more houses via the model service.

    ``features`` is always sent as a JSON list, so the downstream always replies
    with a ``predictions`` list.
    """
    try:
        resp = client.post("/predict", json=features)
        resp.raise_for_status()
        return resp.json()["predictions"]
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Downstream returned %d: %s",
            exc.response.status_code,
            exc.response.text,
        )
        raise HTTPException(
            status_code=503,
            detail="Model service unavailable, please retry later",
        ) from exc
    except httpx.RequestError as exc:
        logger.error("Downstream request failed: %r", exc)
        raise HTTPException(
            status_code=503,
            detail="Model service unavailable, please retry later",
        ) from exc
