const DEFAULT_HEADERS = {
  Accept: "application/json",
};

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(
  /\/$/,
  "",
);

function buildApiUrl(path) {
  if (/^https?:\/\//.test(path)) {
    return path;
  }

  return `${API_BASE_URL}${path}`;
}

export async function apiRequest(path, options = {}) {
  const headers = {
    ...DEFAULT_HEADERS,
    ...options.headers,
  };

  const hasJsonBody = options.body && typeof options.body !== "string";
  if (hasJsonBody) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(buildApiUrl(path), {
    ...options,
    headers,
    body: hasJsonBody ? JSON.stringify(options.body) : options.body,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    const error = new Error(
      payload?.error || `Request failed with status ${response.status}`,
    );
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

/**
 * Fetches the monitored-set overview payload.
 *
 * Returns null when no overview has been materialised yet (404). This keeps
 * callers out of repetitive not-found handling when "no overview yet" is a
 * valid state rather than an operational failure.
 *
 * @returns {Promise<object | null>}
 */
export async function fetchGlobalOverview() {
  try {
    return await apiRequest("/overview");
  } catch (error) {
    if (error.status === 404) return null;
    throw error;
  }
}

/**
 * Fetches the full country detail payload for a single country.
 *
 * Returns null when the country has no briefing yet (404). This lets callers
 * distinguish "not yet materialised" from hard API errors without a try/catch
 * at every call site, and makes it safe to pass as a fetchFn to
 * startBackgroundWarm() in countryDetailCache.js.
 *
 * @param {string} code - ISO country code (uppercase).
 * @returns {Promise<object | null>}
 */
export async function fetchCountryDetail(code) {
  try {
    return await apiRequest(`/countries/${code}`);
  } catch (error) {
    if (error.status === 404) return null;
    throw error;
  }
}
