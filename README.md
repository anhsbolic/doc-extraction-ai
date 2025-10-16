# doc-extraction-ai

### Quick start

1. Copy `.env.example` to `.env` and adjust if needed.
2. `docker compose up --build`

### Health Check

- `GET http://localhost:8080/health-check`
    - `HEALTH_MODE=shallow` -> hanya metadata.
    - `HEALTH_MODE=deep` -> ping Postgres, Redis, MinIO.

### Scripts

```
make build        # build images
make up           # start all containers
make logs         # lihat logs
make exec-api     # masuk ke shell API
make exec-worker  # masuk ke worker
make down         # stop semua
make clean        # bersihin semuanya
make test-health  # cek /health-check
```