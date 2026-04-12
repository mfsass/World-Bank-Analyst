#!/usr/bin/env node
/**
 * World Analyst full-stack deploy orchestrator.
 *
 * Builds all three Docker images via Cloud Build, then deploys:
 *   1. Pipeline Cloud Run Job  (data path — deploy first, no user traffic)
 *   2. API Cloud Run Service   (auth boundary + Firestore reads)
 *   3. Frontend Cloud Run Service  (SPA + same-origin proxy)
 *
 * Cloud Run preserves all existing env vars, secrets, and service accounts
 * unless you pass --set-env-vars / --update-secrets explicitly. This script
 * intentionally omits those flags so routine image updates are safe by default.
 *
 * Usage:
 *   npm run deploy                  # build + deploy all three services
 *   npm run deploy -- --skip-build  # re-deploy current images without rebuilding
 *
 * Environment overrides (optional):
 *   GCP_PROJECT   defaults to "world-bank-analyst"
 *   GCP_REGION    defaults to "europe-west1"
 */

'use strict';

const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const PROJECT   = process.env.GCP_PROJECT ?? 'world-bank-analyst';
const REGION    = process.env.GCP_REGION  ?? 'europe-west1';
const REPO_ROOT = path.resolve(__dirname, '..');
const SKIP_BUILD = process.argv.includes('--skip-build');

// ── gcloud resolution ───────────────────────────────────────────────────────

function findGcloud() {
  // Prefer whatever is on PATH so CI environments work without extra config.
  const probe = spawnSync(
    os.platform() === 'win32' ? 'where' : 'which',
    ['gcloud'],
    { encoding: 'utf8' },
  );
  if (probe.status === 0) return 'gcloud';

  // Windows fallback: try the default Cloud SDK install location.
  if (os.platform() === 'win32') {
    const candidates = [
      path.join(
        process.env.LOCALAPPDATA ?? '',
        'Google', 'Cloud SDK', 'google-cloud-sdk', 'bin', 'gcloud.cmd',
      ),
      'C:\\Program Files (x86)\\Google\\Cloud SDK\\google-cloud-sdk\\bin\\gcloud.cmd',
    ];
    for (const candidate of candidates) {
      if (fs.existsSync(candidate)) return candidate;
    }
  }

  console.error(
    '\n✗  gcloud not found. Install the Google Cloud SDK and make sure it is on your PATH.\n' +
    '   https://cloud.google.com/sdk/docs/install\n',
  );
  process.exit(1);
}

// ── step runner ─────────────────────────────────────────────────────────────

function run(label, cmd, args) {
  console.log(`\n${'─'.repeat(64)}`);
  console.log(`▶  ${label}`);
  console.log('─'.repeat(64));

  // On Windows, .cmd files with spaces in their path need cmd.exe /c to avoid
  // shell tokenisation splitting the path at each space.
  const [spawnCmd, spawnArgs] =
    os.platform() === 'win32' && cmd.toLowerCase().endsWith('.cmd')
      ? ['cmd.exe', ['/c', cmd, ...args]]
      : [cmd, args];

  const result = spawnSync(spawnCmd, spawnArgs, { stdio: 'inherit', cwd: REPO_ROOT });

  if (result.error) {
    console.error(`\n✗  ${label} — could not start process: ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) {
    console.error(`\n✗  ${label} failed (exit ${result.status})`);
    process.exit(result.status ?? 1);
  }
  console.log(`\n✓  ${label}`);
}

// ── deploy sequence ──────────────────────────────────────────────────────────

const gcloud = findGcloud();
const imageBase = `gcr.io/${PROJECT}`;
let step = 1;
const totalSteps = SKIP_BUILD ? 3 : 4;

console.log('\n╔══════════════════════════════════════════════════════════════╗');
console.log('║            World Analyst — deploy                            ║');
console.log('╚══════════════════════════════════════════════════════════════╝');
console.log(`  Project  : ${PROJECT}`);
console.log(`  Region   : ${REGION}`);
console.log(`  Images   : ${SKIP_BUILD ? 'skip (--skip-build)' : 'rebuild via Cloud Build'}`);
console.log(`  Steps    : ${totalSteps}`);

if (!SKIP_BUILD) {
  // Build all three images from repo root so sibling-directory COPYs work.
  run(
    `${step++}/${totalSteps}  Build images (Cloud Build)`,
    gcloud,
    ['builds', 'submit', '.', `--project=${PROJECT}`, '--config=cloudbuild.images.yaml'],
  );
}

// Pipeline job first — no user-facing traffic, safe to update before API/frontend.
run(
  `${step++}/${totalSteps}  Deploy pipeline job`,
  gcloud,
  [
    'run', 'jobs', 'deploy', 'world-analyst-pipeline',
    `--image=${imageBase}/world-analyst-pipeline`,
    `--region=${REGION}`,
    `--project=${PROJECT}`,
  ],
);

run(
  `${step++}/${totalSteps}  Deploy API service`,
  gcloud,
  [
    'run', 'deploy', 'world-analyst-api',
    `--image=${imageBase}/world-analyst-api`,
    `--region=${REGION}`,
    `--project=${PROJECT}`,
  ],
);

run(
  `${step++}/${totalSteps}  Deploy frontend service`,
  gcloud,
  [
    'run', 'deploy', 'world-analyst-frontend',
    `--image=${imageBase}/world-analyst-frontend`,
    `--region=${REGION}`,
    `--project=${PROJECT}`,
  ],
);

console.log('\n╔══════════════════════════════════════════════════════════════╗');
console.log('║  ✅  Deploy complete                                          ║');
console.log('╚══════════════════════════════════════════════════════════════╝\n');
console.log(`  Frontend : https://world-analyst-frontend-v3shswbwpq-ew.a.run.app`);
console.log(`  API      : https://world-analyst-api-v3shswbwpq-ew.a.run.app\n`);
