# Deployment Guide - Derivatives Backend

## Overview
FastAPI backend deployed as a Docker container on Google Cloud Run.

## Prerequisites
- Google Cloud account with billing enabled
- gcloud CLI installed and authenticated
- Docker installed (for local testing)

## Environment Variables

Required for production:

| Variable | Description | Example |
|----------|-------------|---------|
| `TURSO_DATABASE_URL` | Turso database URL | `libsql://market-data-rmeyer1.aws-us-east-1.turso.io` |
| `TURSO_AUTH_TOKEN` | Turso API auth token | `eyJhbG...` |
| `CORS_ORIGINS` | Allowed frontend origins | `https://derivatives-dashboard.vercel.app,http://localhost:3000` |

## Local Docker Testing

```bash
# Build the image
docker build -t derivatives-backend .

# Run locally (with env vars)
docker run -p 8000:8000 \
  -e TURSO_DATABASE_URL="your-db-url" \
  -e TURSO_AUTH_TOKEN="your-token" \
  -e CORS_ORIGINS="http://localhost:3000" \
  derivatives-backend

# Test
curl http://localhost:8000/health
```

## Deploy to Google Cloud Run

### 1. Enable services and configure
```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. Build and push to Google Container Registry
```bash
# Build with Cloud Build (recommended)
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/derivatives-backend

# Or build locally and push
docker build -t gcr.io/YOUR_PROJECT_ID/derivatives-backend .
docker push gcr.io/YOUR_PROJECT_ID/derivatives-backend
```

### 3. Deploy to Cloud Run
```bash
gcloud run deploy derivatives-backend \
  --image gcr.io/YOUR_PROJECT_ID/derivatives-backend \
  --platform managed \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars "TURSO_DATABASE_URL=libsql://market-data-rmeyer1.aws-us-east-1.turso.io" \
  --set-env-vars "TURSO_AUTH_TOKEN=YOUR_TOKEN" \
  --set-env-vars "CORS_ORIGINS=https://derivatives-dashboard.vercel.app" \
  --memory 512Mi \
  --cpu 1 \
  --concurrency 80 \
  --max-instances 10
```

### 4. Get the deployed URL
```bash
gcloud run services describe derivatives-backend --region us-east1 --format 'value(status.url)'
# Example output: https://derivatives-backend-xyz123-ue.a.run.app
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Health check |
| `GET /positions` | Portfolio positions |
| `GET /alerts` | IV spike alerts |
| `GET /dma-data` | Aggregate DMA data |
| `GET /dma-data-by-ticker` | Per-ticker DMA (50/200 day) |
| `GET /iv-data` | IV curve data |
| `GET /iv-data-by-ticker` | Per-ticker IV history |
| `GET /debug/tickers` | Database diagnostic |

## Updating the Deployment

```bash
# Rebuild and redeploy
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/derivatives-backend
gcloud run deploy derivatives-backend \
  --image gcr.io/YOUR_PROJECT_ID/derivatives-backend \
  --region us-east1
```

## Monitoring

- Cloud Run Console: https://console.cloud.google.com/run
- Logs: `gcloud logging read "resource.type=cloud_run_revision"`

## Cost Optimization

Cloud Run scales to zero when not in use. Typical costs:
- Free tier: 2M requests/month, 360K GB-seconds compute
- Beyond free: ~$0.0000025/request + compute time

## Troubleshooting

**CORS errors**: Update `CORS_ORIGINS` env var with your actual Vercel domain

**Database connection fails**: Check `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`

**Container won't start**: Check logs with `gcloud run logs read`
