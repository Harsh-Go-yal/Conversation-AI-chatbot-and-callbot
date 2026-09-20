# Start the API (from repo root). Requires: Docker (Qdrant), Ollama running, .env with keys.
docker compose up -d
Set-Location backend
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8010
