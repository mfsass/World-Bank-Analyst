/**
 * Session-scoped country detail cache shared across the Global Overview,
 * country directory (/country), and the individual country page (/country/:id).
 *
 * Stores full `/countries/{code}` response payloads so navigating to a known
 * market feels immediate — the country page renders from cache while skipping
 * its loading state entirely.
 *
 * No persistent storage. The cache lives only for the current browser session,
 * so a page refresh always pulls fresh data. Per ADR-066, this deliberately
 * avoids a new batch endpoint or cross-session browser persistence.
 *
 * Freshness is tied to the pipeline's `completed_at` timestamp. When that
 * value advances (a new run finished), all cached entries are discarded so the
 * UI never shows pre-run context after a refresh.
 */

// Background warming never issues more than this many simultaneous requests
// so it does not race user-intent or first-paint work.
const CONCURRENCY_CAP = 3;

/** @type {Map<string, { payload: object, generationKey: string | null }>} */
const _cache = new Map();

/** Current pipeline generation key (completed_at). Used for stale detection. */
let _generationKey = null;

/**
 * Session-scoped cache for the `/countries` list. The list contains every
 * tracked market's `{ code, name, ... }` summary. It is the same across all
 * pages, so fetching it once is sufficient for the entire session.
 *
 * @type {Array<{ code: string, name: string }> | null}
 */
let _countriesList = null;

/**
 * Session-scoped cache for the Global Overview first-render snapshot.
 *
 * Stores the panel overview plus the deterministic data the landing surface
 * needs to avoid dropping from skeleton into placeholder copy on re-visit.
 * Cleared alongside all country entries whenever the cache generation advances
 * (i.e. a new pipeline run completes) so stale overview state is never reused
 * after fresh data lands.
 *
 * @type {{
 *   panelOverview: object | null,
 *   countries: Array<{ code: string, name: string }>,
 *   status: object | null,
 *   indicators: object[],
 * } | null}
 */
let _overviewCache = null;

/**
 * Returns the cached `/countries` list, or `null` when it has not been
 * fetched yet this session.
 *
 * @returns {Array<{ code: string, name: string }> | null}
 */
export function getCountriesList() {
  return _countriesList;
}

/**
 * Stores the `/countries` list in the session cache.
 *
 * @param {Array<{ code: string, name: string }>} list - Full `/countries` API response.
 */
export function setCountriesList(list) {
  if (!Array.isArray(list) || !list.length) return;
  _countriesList = list;
}

/**
 * Returns the cached Global Overview first-render snapshot, or `null` when it
 * has not been fetched yet this session.
 *
 * @returns {{
 *   panelOverview: object | null,
 *   countries: Array<{ code: string, name: string }>,
 *   status: object | null,
 *   indicators: object[],
 * } | null}
 */
export function getOverviewCache() {
  return _overviewCache;
}

/**
 * Stores the Global Overview first-render snapshot in the session cache.
 *
 * @param {{
 *   panelOverview: object | null,
 *   countries: Array<{ code: string, name: string }>,
 *   status: object | null,
 *   indicators: object[],
 * }} snapshot - Stable initial snapshot for the Global Overview page.
 */
export function setOverviewCache(snapshot) {
  if (!snapshot) return;
  _overviewCache = snapshot;
}

/**
 * Returns the cached country detail payload for `code`, or `undefined` when
 * the entry has not been warmed yet.
 *
 * @param {string} code - ISO country code (case-insensitive).
 * @returns {object | undefined}
 */
export function getCachedCountry(code) {
  return _cache.get(code?.toUpperCase())?.payload;
}

/**
 * Stores a country detail payload in the session cache.
 *
 * @param {string} code - ISO country code (case-insensitive).
 * @param {object} payload - Full `/countries/{code}` API response.
 * @param {string | null} [generationKey] - Pipeline `completed_at` value.
 *   Stored alongside the payload so stale entries can be detected when the
 *   pipeline advances.
 */
export function setCachedCountry(code, payload, generationKey = null) {
  if (!code || !payload) return;
  _cache.set(code.toUpperCase(), {
    payload,
    generationKey: generationKey ?? _generationKey,
  });
}

/**
 * Advances the cache generation key.
 *
 * When `nextKey` is newer than the current key, all cached entries are
 * discarded so the UI pulls fresh pipeline data after the next run. No-ops
 * when `nextKey` is null, empty, or already matches the current generation.
 *
 * @param {string | null} nextKey - Latest pipeline `completed_at` value.
 */
export function updateCacheGeneration(nextKey) {
  if (!nextKey || nextKey === _generationKey) return;
  _cache.clear();
  _overviewCache = null;
  _generationKey = nextKey;
}

/**
 * Resets the session-scoped frontend caches.
 *
 * Used by tests so each scenario starts from a clean browser-session model
 * instead of inheriting warmed entries from a previous case.
 */
export function resetCountryDetailCache() {
  _cache.clear();
  _countriesList = null;
  _overviewCache = null;
  _generationKey = null;
}

/**
 * Returns true when the given country code is already warmed in the cache.
 *
 * @param {string} code - ISO country code (case-insensitive).
 * @returns {boolean}
 */
export function isCountryWarmed(code) {
  return _cache.has(code?.toUpperCase());
}

/**
 * Starts background preloading of country detail payloads for an ordered list
 * of country codes.
 *
 * - Codes already in the cache are skipped.
 * - Concurrency is capped at CONCURRENCY_CAP (3) so background fetches never
 *   delay first-paint or user-intent requests.
 * - Fetch errors are silently swallowed — the country page falls back to its
 *   own fetch when the cache entry is absent.
 * - Warming is deferred to an idle callback (or a short setTimeout fallback)
 *   so it never runs on the same call stack as page initialisation.
 *
 * @param {string[]} orderedCodes - Codes to warm, highest priority first.
 *   Already-cached codes are skipped automatically.
 * @param {(code: string) => Promise<object | null>} fetchFn - Fetches a single
 *   country detail payload. Must return null (not throw) for a 404.
 * @param {string | null} [generationKey] - Pipeline generation key to tag
 *   each cached entry so stale detection works correctly.
 */
export function startBackgroundWarm(
  orderedCodes,
  fetchFn,
  generationKey = null,
) {
  const queue = orderedCodes.filter((code) => code && !isCountryWarmed(code));
  if (!queue.length) return;

  async function runQueue() {
    for (let i = 0; i < queue.length; i += CONCURRENCY_CAP) {
      const batch = queue.slice(i, i + CONCURRENCY_CAP);
      // Settle the full batch before starting the next group so we never
      // exceed CONCURRENCY_CAP simultaneous requests.
      await Promise.allSettled(
        batch.map(async (code) => {
          try {
            const payload = await fetchFn(code);
            if (payload) setCachedCountry(code, payload, generationKey);
          } catch {
            // Background failure is non-fatal — country page retries on load.
          }
        }),
      );
    }
  }

  // Defer to an idle callback so warming never competes with the first render.
  if (typeof requestIdleCallback !== "undefined") {
    requestIdleCallback(
      () => {
        void runQueue();
      },
      { timeout: 2000 },
    );
  } else {
    setTimeout(() => {
      void runQueue();
    }, 200);
  }
}
