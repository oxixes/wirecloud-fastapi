# Docker deployment

This directory contains a complete Docker setup for Wirecloud FastAPI:

- `Dockerfile`: multi-stage image build (frontend assets + python wheel)
- `settings.py`: environment-driven runtime settings
- `entrypoint.sh`: initializes writable directories and starts the app
- `docker-compose.yml`: Wirecloud + MongoDB + Elasticsearch stack
- `.env.example`: environment variable template

## Quick start

1. Create env file:

```bash
cp docker/.env.example docker/.env
```

2. Start the stack:

```bash
cd docker
docker compose up -d --build
```

3. Open Wirecloud:

- `http://localhost:8000`

## Notes

- `settings.py` is loaded through `PYTHONPATH=/app/docker` in the image.
- Change `WIRECLOUD_SECRET_KEY` and `WIRECLOUD_JWT_KEY` in production.
- Persistent app data is stored in the `wirecloud_data` docker volume.
