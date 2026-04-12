/**
 * World Analyst — local dev runner.
 *
 * Opens the frontend and/or API backend in separate terminal windows so you
 * can watch both output streams independently. Uses Windows cmd /c start so
 * each window is independent and can be closed individually.
 *
 * Usage:
 *   node scripts/dev.js            # frontend + backend (local API, port 8080)
 *   node scripts/dev.js --prod     # frontend only, proxied to production API
 *   node scripts/dev.js --front    # frontend only (expects local API running)
 *   node scripts/dev.js --back     # backend only
 *
 * Shortcuts via root package.json:
 *   npm run app                    # full local stack
 *   npm run app:prod               # frontend → prod API
 *   npm run frontend               # frontend only
 *   npm run backend                # backend only
 *
 * Production mode prerequisites:
 *   Create frontend/.env.prod.local (gitignored) with:
 *     WORLD_ANALYST_API_UPSTREAM=https://world-analyst-api-v3shswbwpq-ew.a.run.app
 *     WORLD_ANALYST_DEV_PROXY_API_KEY=<api-key>
 *   The Vite dev server picks this file up automatically when --mode prod is passed.
 */

"use strict";

const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const ROOT = path.resolve(__dirname, "..");
const args = process.argv.slice(2);
const isProd = args.includes("--prod");
const frontOnly = isProd || args.includes("--front");
const backOnly = args.includes("--back");

// ─── Preflight checks ────────────────────────────────────────────────────────

if (isProd) {
  const envFile = path.join(ROOT, "frontend", ".env.prod.local");
  if (!fs.existsSync(envFile)) {
    console.error(
      "\n  ✗  frontend/.env.prod.local not found.\n" +
        "     Create it with:\n" +
        "       WORLD_ANALYST_API_UPSTREAM=https://world-analyst-api-v3shswbwpq-ew.a.run.app\n" +
        "       WORLD_ANALYST_DEV_PROXY_API_KEY=<your-api-key>\n"
    );
    process.exit(1);
  }
}

// ─── Window spawner ──────────────────────────────────────────────────────────

/**
 * Open a new cmd window that stays open after the command exits.
 *
 * Passes a single shell string to `cmd /c` so that `start` correctly
 * treats the first double-quoted token as the window title rather than
 * trying to resolve it as an executable (Windows quoting edge case).
 *
 * @param {string} title - Window title bar text.
 * @param {string} command - Shell command to run inside the new window.
 */
function openWindow(title, command) {
  // windowsVerbatimArguments prevents Node from escaping the quotes inside the
  // shell string, which would turn `"title"` into `\"title\"` and cause Windows
  // to try to resolve the title as an executable name.
  const proc = spawn(
    "cmd.exe",
    ["/c", `start "${title}" cmd /k ${command}`],
    { cwd: ROOT, detached: true, stdio: "ignore", windowsVerbatimArguments: true }
  );
  proc.unref();
}

// ─── Commands ────────────────────────────────────────────────────────────────

const FRONTEND_DIR = path.join(ROOT, "frontend");
const API_DIR = path.join(ROOT, "api");

// --mode prod tells Vite to load frontend/.env.prod.local, which sets
// WORLD_ANALYST_API_UPSTREAM → production API and the matching API key.
const frontendCmd = isProd
  ? `cd /d "${FRONTEND_DIR}" && npx vite --mode prod`
  : `cd /d "${FRONTEND_DIR}" && npm run dev`;

const backendCmd = `cd /d "${API_DIR}" && python app.py`;

// ─── Output ──────────────────────────────────────────────────────────────────

const modeLabel = isProd ? "app:prod  ->  production API" : "app  ->  local stack";

console.log("");
console.log("╔══════════════════════════════════════════════════════════════╗");
console.log(
  `║  World Analyst - ${modeLabel}`.padEnd(63) + "║"
);
console.log("╚══════════════════════════════════════════════════════════════╝");

if (!backOnly) {
  const label = isProd
    ? "World Analyst - Frontend (prod API)"
    : "World Analyst - Frontend";
  console.log(`\n  ▶  ${label}`);
  console.log(`     ${frontendCmd}`);
  openWindow(label, frontendCmd);
}

if (!frontOnly) {
  const label = "World Analyst - Backend (API :8080)";
  console.log(`\n  ▶  ${label}`);
  console.log(`     ${backendCmd}`);
  openWindow(label, backendCmd);
}

console.log("");
if (isProd) {
  console.log("  Frontend (→ prod API) : http://localhost:5173");
} else {
  console.log("  Frontend : http://localhost:5173");
  if (!frontOnly) {
    console.log("  Backend  : http://localhost:8080");
  }
}
console.log("");
