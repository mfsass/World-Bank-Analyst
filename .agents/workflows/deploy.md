---
description: Deploy World Analyst to Cloud Run with explicit Firestore, GCS, and frontend-proxy config
---

## Scope

This workflow prepares a truthful cloud rollout for the current repo state:

- API on Cloud Run
- Frontend on Cloud Run behind the nginx same-origin proxy
- Pipeline on a Cloud Run Job
- Firestore for processed records
- GCS for raw World Bank archives
- Secret Manager for the shared API key
- Secret Manager for the pipeline AI provider credential

The live AI path is already implemented in the repo. Cloud deployment must therefore provide the pipeline job with a provider credential such as `GEMINI_API_KEY` for the default Google baseline, or the corresponding OpenAI secret when the provider is switched deliberately.

## Required user-side setup before deployment

1. GCP project with billing enabled
2. Firestore Native database
3. GCS bucket for raw archives
4. Secret Manager secret for the shared API key
5. Service accounts for:
   - API service
   - Pipeline job
   - Cloud Scheduler

## Suggested environment variables

```bash
export PROJECT_ID=[your-project-id]
export REGION=europe-west1
export FIRESTORE_COLLECTION=insights
export RAW_ARCHIVE_BUCKET=[your-raw-archive-bucket]
export FRONTEND_ORIGIN=[your-frontend-url]
export API_KEY_SECRET=world-analyst-api-key
export GEMINI_API_KEY_SECRET=world-analyst-gemini-api-key
export API_SERVICE_ACCOUNT=world-analyst-api@$PROJECT_ID.iam.gserviceaccount.com
export PIPELINE_SERVICE_ACCOUNT=world-analyst-pipeline@$PROJECT_ID.iam.gserviceaccount.com
export SCHEDULER_SERVICE_ACCOUNT=world-analyst-scheduler@$PROJECT_ID.iam.gserviceaccount.com
```

## One-time project bootstrap

```bash
gcloud config set project $PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com firestore.googleapis.com secretmanager.googleapis.com cloudscheduler.googleapis.com storage.googleapis.com
```

Create the Firestore database and the GCS bucket before the first deploy. The exact Firestore creation step can vary by project posture, but the database must exist before the API or pipeline runs in `REPOSITORY_MODE=firestore`.

Create the service accounts up front so Cloud Run and Cloud Scheduler can use least-privilege identities:

```bash
gcloud iam service-accounts create world-analyst-api --display-name="World Analyst API"
gcloud iam service-accounts create world-analyst-pipeline --display-name="World Analyst Pipeline"
gcloud iam service-accounts create world-analyst-scheduler --display-name="World Analyst Scheduler"
```

Example bucket command:

```bash
gcloud storage buckets create gs://$RAW_ARCHIVE_BUCKET --location=$REGION --uniform-bucket-level-access
```

Create the shared API key secret before deploying the API or frontend proxy:

```bash
printf '%s' '[choose-a-shared-api-key]' | gcloud secrets create $API_KEY_SECRET --data-file=-
```

Create the live AI credential secret before deploying the pipeline job:

```bash
printf '%s' '[your-gemini-api-key]' | gcloud secrets create $GEMINI_API_KEY_SECRET --data-file=-
```

Grant the minimum roles needed for this phase:

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$API_SERVICE_ACCOUNT" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$API_SERVICE_ACCOUNT" \
  --role="roles/run.invoker"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$API_SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$PIPELINE_SERVICE_ACCOUNT" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$PIPELINE_SERVICE_ACCOUNT" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$PIPELINE_SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SCHEDULER_SERVICE_ACCOUNT" \
  --role="roles/run.invoker"
```

## Build images

```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/world-analyst-api ./api
gcloud builds submit --tag gcr.io/$PROJECT_ID/world-analyst-frontend ./frontend
gcloud builds submit --tag gcr.io/$PROJECT_ID/world-analyst-pipeline ./pipeline
```

## Deploy API service

The API service must stay explicit about production auth, allowed origins, and Firestore mode.

```bash
gcloud run deploy world-analyst-api \
  --image gcr.io/$PROJECT_ID/world-analyst-api \
  --region $REGION \
  --min-instances 0 \
  --allow-unauthenticated \
  --service-account $API_SERVICE_ACCOUNT \
  --set-env-vars WORLD_ANALYST_RUNTIME_ENV=production,REPOSITORY_MODE=firestore,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,WORLD_ANALYST_FIRESTORE_COLLECTION=$FIRESTORE_COLLECTION,WORLD_ANALYST_ALLOWED_ORIGINS=$FRONTEND_ORIGIN \
  --update-secrets WORLD_ANALYST_API_KEY=$API_KEY_SECRET:latest
```

## Deploy pipeline job

The repo default stays local. Cloud Run must opt into the real fetch path and Firestore storage explicitly.

```bash
gcloud run jobs deploy world-analyst-pipeline \
  --image gcr.io/$PROJECT_ID/world-analyst-pipeline \
  --region $REGION \
  --service-account $PIPELINE_SERVICE_ACCOUNT \
  --tasks 1 \
  --max-retries 0 \
  --memory 512Mi \
  --cpu 1 \
  --task-timeout 10m \
  --set-env-vars PIPELINE_MODE=live,REPOSITORY_MODE=firestore,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,WORLD_ANALYST_FIRESTORE_COLLECTION=$FIRESTORE_COLLECTION,WORLD_ANALYST_RAW_ARCHIVE_BUCKET=$RAW_ARCHIVE_BUCKET \
  --update-secrets GEMINI_API_KEY=$GEMINI_API_KEY_SECRET:latest
```

## Deploy frontend service

`frontend/nginx/default.conf.template` already proxies `/api/v1/` and injects the API key server-side. The upstream value must include the Connexion base path.

```bash
export API_ORIGIN=[https://world-analyst-api-<hash>-$REGION.run.app]

gcloud run deploy world-analyst-frontend \
  --image gcr.io/$PROJECT_ID/world-analyst-frontend \
  --region $REGION \
  --min-instances 0 \
  --allow-unauthenticated \
  --set-env-vars WORLD_ANALYST_API_UPSTREAM=$API_ORIGIN/api/v1/ \
  --update-secrets WORLD_ANALYST_PROXY_API_KEY=$API_KEY_SECRET:latest
```

## Create the monthly scheduler

The bounded annual World Bank data does not justify weekly or daily reruns. Use the first Monday of each month at 06:00 UTC.

```bash
gcloud scheduler jobs create http world-analyst-monthly \
  --location=$REGION \
  --schedule="0 6 1-7 * MON" \
  --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/world-analyst-pipeline:run" \
  --http-method=POST \
  --oauth-service-account-email=$SCHEDULER_SERVICE_ACCOUNT
```

## Validation checklist

- `GET /api/v1/health` succeeds from the deployed API
- Frontend requests hit `/api/v1/...` through nginx, not the API origin directly
- `GET /api/v1/pipeline/status` reads from Firestore-backed state
- A manual Cloud Run Job execution writes documents to Firestore and raw archives to GCS
- The pipeline job can authenticate to the configured live AI provider without baking credentials into images
- No frontend asset contains the shared API key
