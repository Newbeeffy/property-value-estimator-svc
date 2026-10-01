# Property Value Estimator Service

A FastAPI facade that sits in front of the `house-price-predict-svc` (Task 1).
It does **not** train or serve a model itself — it validates property details,
delegates prediction to the downstream model service over HTTP, and persists an
estimate history in SQLite.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/estimates` | POST | Validate + predict a single property, persist result |
| `/estimates/batch` | POST | Predict multiple properties in one round-trip (comparison view) |
| `/estimates` | GET | List estimate history (newest first) |
| `/estimates/{id}` | GET | Fetch one estimate |
| `/estimates/{id}` | DELETE | Delete one estimate |

## Example

```bash
curl -X POST http://localhost:8000/estimates \
  -H "Content-Type: application/json" \
  -d '{"square_footage":1850,"bedrooms":3,"bathrooms":2,"year_built":1998,
       "lot_size":7500,"distance_to_city_center":5.6,"school_rating":8.2}'
# -> {"id":"...","inputs":{...},"prediction":265000.0,"created_at":"..."}
```

## Project Layout

```
app/            Application code (packaged into the image)
tests/          API tests (downstream mocked with respx)
charts/         Helm chart (k8s deployment + PVC)
requirements*.txt
Dockerfile
```

## Configuration

Read from environment variables (injected by the Helm chart):

| Variable | Default | Purpose |
|----------|---------|---------|
| `MODEL_SERVICE_URL` | `http://house-price-predict-svc` | Downstream model service |
| `MODEL_SERVICE_TIMEOUT` | `5.0` | Per-call timeout (seconds) |
| `DB_PATH` | `/data/estimates.db` | SQLite file location |
| `MAX_BATCH_SIZE` | `50` | Max properties per batch request |

## Development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Run locally (requires the downstream service to be reachable)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run unit tests
python -m pytest
```

## Build & Deploy (k3s/k8s)

```bash
docker build -t interview/property-value-estimator-svc:latest .
docker save interview/property-value-estimator-svc:latest -o property-value-estimator-svc.tar
sudo k3s ctr images import property-value-estimator-svc.tar

helm install property-value-estimator-svc ./charts

# Verify
kubectl get pods
kubectl port-forward svc/property-value-estimator-svc 8080:80
curl http://localhost:8080/health
```
