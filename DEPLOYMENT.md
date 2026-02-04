# Derivatives Backend Deployment Guide

This guide provides step-by-step instructions for deploying the derivatives backend API to Google Cloud Run.

## Prerequisites

- Google Cloud SDK installed and configured
- Docker installed
- Access to a Turso database

## Environment Variables

Before deploying, ensure you have the following environment variables:

- `TURSO_DATABASE_URL` - URL for your Turso database
- `TURSO_AUTH_TOKEN` - Authentication token for your Turso database
- `CORS_ORIGINS` - Comma-separated list of allowed origins (e.g., your frontend domain)

## Deployment Methods

### Option 1: Google Cloud Build (Recommended)

1. Ensure your repository has the `cloudbuild.yaml` file
2. Set up the required substitutions in Cloud Build:
   - `_TURSO_DATABASE_URL`
   - `_TURSO_AUTH_TOKEN`
3. Trigger the build via:
   ```
   gcloud builds submit --config cloudbuild.yaml
   ```

### Option 2: Manual Docker Deployment

1. Build the Docker image:
   ```
   docker build -t derivatives-backend .
   ```

2. Run locally for testing:
   ```
   docker run -p 8000:8000 \
     -e TURSO_DATABASE_URL=your_database_url \
     -e TURSO_AUTH_TOKEN=your_auth_token \
     -e CORS_ORIGINS=your_frontend_domain \
     derivatives-backend
   ```

3. Tag and push to Google Container Registry:
   ```
   docker tag derivatives-backend gcr.io/your-project-id/derivatives-backend
   docker push gcr.io/your-project-id/derivatives-backend
   ```

4. Deploy to Cloud Run:
   ```
   gcloud run deploy derivatives-backend \
     --image gcr.io/your-project-id/derivatives-backend \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars TURSO_DATABASE_URL=your_database_url,TURSO_AUTH_TOKEN=your_auth_token,CORS_ORIGINS=your_frontend_domain
   ```

## API Endpoints

Once deployed, your API will be accessible at:
- Base URL: `https://your-service-url.a.run.app`
- Health check: `GET /`
- API routes: Defined in `api/routes.py`

Replace `your-service-url` with the actual URL provided by Cloud Run after deployment.