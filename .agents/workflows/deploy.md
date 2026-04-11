---
description: Deploy World Analyst services to GCP Cloud Run
---

## Prerequisites
- `gcloud` CLI authenticated
- GCP project ID confirmed with user
- Docker images built

## Steps

1. Set GCP project
```bash
gcloud config set project $PROJECT_ID
```

2. Enable required APIs
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com firestore.googleapis.com secretmanager.googleapis.com cloudscheduler.googleapis.com
```

3. Build and deploy API service
```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/world-analyst-api ./api
gcloud run deploy world-analyst-api --image gcr.io/$PROJECT_ID/world-analyst-api --region europe-west1 --min-instances 0 --allow-unauthenticated
```

4. Build and deploy frontend service
```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/world-analyst-frontend ./frontend
gcloud run deploy world-analyst-frontend --image gcr.io/$PROJECT_ID/world-analyst-frontend --region europe-west1 --min-instances 0 --allow-unauthenticated
```

5. Deploy pipeline as Cloud Run Job
```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/world-analyst-pipeline ./pipeline
gcloud run jobs create world-analyst-pipeline --image gcr.io/$PROJECT_ID/world-analyst-pipeline --region europe-west1
```

6. Create Cloud Scheduler trigger (weekly)
```bash
gcloud scheduler jobs create http world-analyst-weekly --schedule="0 6 * * MON" --uri="https://europe-west1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/world-analyst-pipeline:run" --http-method=POST --oauth-service-account-email=$SERVICE_ACCOUNT
```
