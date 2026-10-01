"""Runtime configuration, read from environment variables."""
from __future__ import annotations

import os

MODEL_SERVICE_URL: str = os.environ.get(
    "MODEL_SERVICE_URL", "http://house-price-predict-svc"
)

# Timeout (seconds) for each call to the downstream model service.
MODEL_SERVICE_TIMEOUT: float = float(os.environ.get("MODEL_SERVICE_TIMEOUT", "5.0"))

# SQLite file backing the estimate history.
DB_PATH: str = os.environ.get("DB_PATH", "/data/estimates.db")

# Upper bound on the number of properties accepted in a single batch request.
MAX_BATCH_SIZE: int = int(os.environ.get("MAX_BATCH_SIZE", "50"))
