const DEFAULT_HEADERS = {
  Accept: "application/json",
  "X-API-Key": "local-dev",
};

export async function apiRequest(path, options = {}) {
  const headers = {
    ...DEFAULT_HEADERS,
    ...options.headers,
  };

  const hasJsonBody = options.body && typeof options.body !== "string";
  if (hasJsonBody) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(path, {
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
