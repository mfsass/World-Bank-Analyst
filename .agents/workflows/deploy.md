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

## Deployment model at a glance

Use this mental model before you run any commands:

| Surface | What it owns | What it must know |
| --- | --- | --- |
| API service | Browser-facing auth boundary, Firestore reads, manual pipeline dispatch | Production auth config, allowed frontend origin, Firestore mode, Cloud Run Job coordinates |
| Pipeline job | World Bank fetch, Pandas analysis, AI synthesis, Firestore writes, GCS raw archives | `PIPELINE_MODE=live`, Firestore project/collection, raw archive bucket, provider secret |
| Frontend service | SPA delivery and same-origin `/api/v1/` proxy | API upstream including `/api/v1/`, proxy API key, production runtime flag |
| Cloud Scheduler | Time-based job trigger | Job URI, scheduler service account, OAuth scope for the Cloud Run Jobs API |

The key split is deliberate: the frontend never owns the shared API key in browser code, the API never runs the full pipeline inline in cloud mode, and the pipeline job is the only surface that needs the provider credential plus raw archive storage.

## Required user-side setup before deployment

1. GCP project with billing enabled
2. Firestore Native database
3. GCS bucket for raw archives
4. Secret Manager secret for the shared API key
5. Service accounts for:
   - API service
   - Frontend service
   - Pipeline job
   - Cloud Scheduler

## Lessons from the first live rollout

1. **Build from the repo root.** The API and pipeline Dockerfiles copy sibling directories, so nested `gcloud builds submit` calls are the wrong mental model. The working path is the repo root plus `cloudbuild.images.yaml`.
2. **Treat override-based dispatch as a different IAM problem.** The manual trigger does not just invoke a job; it passes runtime overrides. That is why the API service account needed `run.jobs.runWithOverrides`, and why `roles/run.developer` worked while `roles/run.invoker` did not.
3. **Treat the frontend proxy as a runtime concern, not a build concern.** In Cloud Run, the frontend must receive `WORLD_ANALYST_RUNTIME_ENV=production`, `WORLD_ANALYST_API_UPSTREAM`, and `WORLD_ANALYST_PROXY_API_KEY` explicitly. Leaving the container on local fallbacks is a deployment error, not a harmless default.
4. **Firestore mode is coupled to raw archive storage.** The deployed record shape keeps raw backup references alongside processed documents. In practice that means Firestore mode without the GCS bucket is an incomplete deployment.
5. **Scheduler needs the Cloud Run Jobs API scope.** The scheduler service account is not enough on its own; the HTTP job trigger also needed `--oauth-token-scope=https://www.googleapis.com/auth/cloud-platform` in the working command.
6. **A green deploy is not a finished rollout.** The release is only truthful after the smoke gate proves the direct API health path, the frontend-proxied 17-country read, a clean manual trigger to terminal `complete`, same-origin browser traffic, and no shared key in the built assets.

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
export FRONTEND_SERVICE_ACCOUNT=world-analyst-frontend@$PROJECT_ID.iam.gserviceaccount.com
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
gcloud iam service-accounts create world-analyst-frontend --display-name="World Analyst Frontend"
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

Grant the roles needed for this phase:

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$API_SERVICE_ACCOUNT" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$API_SERVICE_ACCOUNT" \
  --role="roles/run.developer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$API_SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$FRONTEND_SERVICE_ACCOUNT" \
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

`POST /api/v1/pipeline/trigger` dispatches the Cloud Run Job with runtime overrides, so the API service account needs `run.jobs.runWithOverrides`. In practice that means `roles/run.invoker` is not enough for the API service; the built-in role that worked in the live rollout is `roles/run.developer`.

## Build images

```bash
# The API and pipeline Dockerfiles copy sibling directories, so image builds
# must run from the repo root. `cloudbuild.images.yaml` keeps that context
# explicit and works even when a local Docker daemon is unavailable.
gcloud builds submit . --project $PROJECT_ID --config cloudbuild.images.yaml
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
  --set-env-vars WORLD_ANALYST_RUNTIME_ENV=production,REPOSITORY_MODE=firestore,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,WORLD_ANALYST_FIRESTORE_COLLECTION=$FIRESTORE_COLLECTION,WORLD_ANALYST_ALLOWED_ORIGINS=$FRONTEND_ORIGIN,WORLD_ANALYST_PIPELINE_DISPATCH_MODE=cloud,WORLD_ANALYST_PIPELINE_JOB_PROJECT_ID=$PROJECT_ID,WORLD_ANALYST_PIPELINE_JOB_REGION=$REGION,WORLD_ANALYST_PIPELINE_JOB_NAME=world-analyst-pipeline \
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

`frontend/nginx/default.conf.template` already proxies `/api/v1/` and injects the API key server-side. The upstream value must include the Connexion base path. The frontend should run as its own service account because nginx reads `WORLD_ANALYST_PROXY_API_KEY` from Secret Manager at runtime, and the container now fails fast in non-local runtimes if either proxy variable is left on its local fallback.

```bash
export API_ORIGIN=[https://world-analyst-api-<hash>-$REGION.run.app]

gcloud run deploy world-analyst-frontend \
  --image gcr.io/$PROJECT_ID/world-analyst-frontend \
  --region $REGION \
  --min-instances 0 \
  --allow-unauthenticated \
  --service-account $FRONTEND_SERVICE_ACCOUNT \
  --set-env-vars WORLD_ANALYST_RUNTIME_ENV=production,WORLD_ANALYST_API_UPSTREAM=$API_ORIGIN/api/v1/ \
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
  --oauth-service-account-email=$SCHEDULER_SERVICE_ACCOUNT \
  --oauth-token-scope=https://www.googleapis.com/auth/cloud-platform
```

## Release smoke gate

Any failed step below blocks the deployment from being described as review-ready.

```bash
export FRONTEND_URL=[https://world-analyst-frontend-<hash>-$REGION.run.app]
export API_ORIGIN=[https://world-analyst-api-<hash>-$REGION.run.app]
export API_KEY_VALUE=$(gcloud secrets versions access latest --secret=$API_KEY_SECRET)
```

1. **Direct API health and auth boundary**

   ```bash
   curl -fsS $API_ORIGIN/api/v1/health > /dev/null
   test "$(curl -s -o /dev/null -w "%{http_code}" $API_ORIGIN/api/v1/countries)" = "401"
   ```

   Success: the public health path responds and the protected countries endpoint rejects callers that bypass the proxy boundary.

2. **Authenticated dashboard read through the frontend proxy**

   ```bash
   python - <<'PY'
   import json
   import os
   import urllib.request

   frontend_url = os.environ["FRONTEND_URL"].rstrip("/")
   with urllib.request.urlopen(f"{frontend_url}/api/v1/countries") as response:
       countries = json.load(response)

   assert len(countries) == 17, len(countries)
   print("countries-ok")
   PY
   ```

   Success: the same-origin proxy returns the full 17-country panel without the browser holding the shared key.

3. **Manual trigger and terminal status**

   ```bash
   curl -fsS -X POST $FRONTEND_URL/api/v1/pipeline/trigger > /tmp/world-analyst-trigger.json

   for attempt in $(seq 1 40); do
     STATUS=$(curl -fsS $FRONTEND_URL/api/v1/pipeline/status)
     echo "$STATUS"
     echo "$STATUS" | grep -q '"status":"running"' || break
     sleep 15
   done

   echo "$STATUS" | grep -q '"status":"complete"'
   ```

   Success: the trigger flow runs through the frontend proxy and reaches a clean terminal `complete` state. Any terminal `failed` status is a release blocker until the root cause is understood.

4. **Browser same-origin proof**

   Open `$FRONTEND_URL` in the browser, refresh once, and inspect DevTools -> Network.

   Success: the browser only calls `/api/v1/...` on the frontend origin, and the browser-visible request headers do not contain `X-API-Key`.

5. **Frontend bundle secret check**

   ```bash
   python - <<'PY'
   import os
   import re
   import urllib.request

   frontend_url = os.environ["FRONTEND_URL"].rstrip("/")
   shared_key = os.environ["API_KEY_VALUE"]

   html = urllib.request.urlopen(frontend_url).read().decode("utf-8", "ignore")
   asset_paths = re.findall(r'/assets/[^"\']+\.(?:js|css)', html)
   bundle = "".join(
       urllib.request.urlopen(f"{frontend_url}{path}").read().decode("utf-8", "ignore")
       for path in asset_paths
   )

   if shared_key in bundle:
       raise SystemExit("Shared API key found in frontend assets.")

   print("bundle-ok")
   PY
   ```

   Success: the fetched frontend assets do not contain the shared API key.
