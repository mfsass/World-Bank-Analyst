import Flag from "react-world-flags";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { StatusPill } from "../components/StatusPill";
import { apiRequest, fetchCountryDetail, fetchGlobalOverview } from "../api";
import {
  getCachedCountry,
  getCountriesList,
  getOverviewCache,
  setCachedCountry,
  setCountriesList,
  setOverviewCache,
  startBackgroundWarm,
} from "../lib/countryDetailCache";
import { getOutlookTone } from "./globalOverviewModel";

function getCachedMaterializedCodes() {
  const cachedOverview = getOverviewCache();
  const cachedCodes = cachedOverview?.panelOverview?.country_codes ?? [];
  return new Set(cachedCodes.map((code) => code.toUpperCase()));
}

function hasCachedDirectorySnapshot(countries) {
  const cachedOverview = getOverviewCache();
  return Boolean(
    cachedOverview &&
      "panelOverview" in cachedOverview &&
      Array.isArray(countries) &&
      countries.length,
  );
}

function getCachedOutlookMap(materializedCodeSet) {
  const nextOutlookMap = {};

  materializedCodeSet.forEach((code) => {
    const cachedBriefing = getCachedCountry(code);
    if (cachedBriefing?.outlook) {
      nextOutlookMap[code] = cachedBriefing.outlook;
    }
  });

  return nextOutlookMap;
}

function getPendingOutlookCodes(materializedCodeSet, outlookMap) {
  return [...materializedCodeSet].filter((code) => !outlookMap[code]);
}

export function CountryIntelligenceLanding() {
  const initialMaterializedCodes = getCachedMaterializedCodes();
  const initialOutlookMap = getCachedOutlookMap(initialMaterializedCodes);
  const [countries, setCountries] = useState(() => getCountriesList() ?? []);
  const [materializedCodes, setMaterializedCodes] = useState(
    getCachedMaterializedCodes,
  );
  const [outlookByCode, setOutlookByCode] = useState(() => initialOutlookMap);
  const [loadingOutlookCodes, setLoadingOutlookCodes] = useState(() =>
    getPendingOutlookCodes(initialMaterializedCodes, initialOutlookMap),
  );
  const [viewState, setViewState] = useState(() =>
    hasCachedDirectorySnapshot(getCountriesList() ?? []) ? "ready" : "loading",
  );
  const [requestError, setRequestError] = useState("");
  const [query, setQuery] = useState("");
  const searchRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    let isActive = true;
    const startedFromCache = hasCachedDirectorySnapshot(getCountriesList() ?? []);

    async function loadDirectory() {
      try {
        const [countriesList, overview] = await Promise.all([
          apiRequest("/countries"),
          fetchGlobalOverview(),
        ]);

        if (!isActive) {
          return;
        }

        setCountries(countriesList);
        setCountriesList(countriesList);
        setOverviewCache({
          panelOverview: overview,
          countries: countriesList,
          status: getOverviewCache()?.status ?? null,
          indicators: getOverviewCache()?.indicators ?? [],
        });
        const nextMaterializedCodes = new Set(
          (overview?.country_codes ?? []).map((code) => code.toUpperCase()),
        );
        const cachedOutlooks = getCachedOutlookMap(nextMaterializedCodes);
        const pendingOutlookCodes = getPendingOutlookCodes(
          nextMaterializedCodes,
          cachedOutlooks,
        );

        setMaterializedCodes(nextMaterializedCodes);
        setOutlookByCode((currentOutlooks) => ({
          ...currentOutlooks,
          ...cachedOutlooks,
        }));
        setLoadingOutlookCodes(pendingOutlookCodes);
        setViewState("ready");
        setRequestError("");

        pendingOutlookCodes.forEach((code) => {
          void fetchCountryDetail(code)
            .then((briefing) => {
              if (!isActive || !briefing) {
                return;
              }

              setCachedCountry(code, briefing);
              if (briefing.outlook) {
                setOutlookByCode((currentOutlooks) => ({
                  ...currentOutlooks,
                  [code]: briefing.outlook,
                }));
              }
            })
            .catch(() => {})
            .finally(() => {
              if (!isActive) {
                return;
              }

              setLoadingOutlookCodes((currentCodes) =>
                currentCodes.filter((currentCode) => currentCode !== code),
              );
            });
        });

        // Warm non-materialised country pages only after the directory is
        // stable. Materialised countries are already being fetched above for
        // their final outlook labels, so excluding them avoids duplicate work.
        startBackgroundWarm(
          countriesList
            .map((country) => country.code)
            .filter((code) => !nextMaterializedCodes.has(code.toUpperCase())),
          fetchCountryDetail,
        );
      } catch (error) {
        if (!isActive) {
          return;
        }

        if (startedFromCache) {
          setRequestError(error.message);
          return;
        }

        setViewState("error");
        setRequestError(error.message);
      }
    }

    void loadDirectory();

    return () => {
      isActive = false;
    };
  }, []);

  /* Global "/" shortcut to focus the search input. */
  useEffect(() => {
    function handleKeyDown(e) {
      if (
        e.key === "/" &&
        document.activeElement?.tagName !== "INPUT" &&
        document.activeElement?.tagName !== "TEXTAREA"
      ) {
        e.preventDefault();
        searchRef.current?.focus();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  /* Filter and sort countries: materialized first, then alphabetical. */
  const filteredCountries = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = countries.filter(
      (c) =>
        !q ||
        c.name.toLowerCase().includes(q) ||
        c.code.toLowerCase().includes(q),
    );

    return filtered.sort((a, b) => {
      const aMat = materializedCodes.has(a.code.toUpperCase()) ? 0 : 1;
      const bMat = materializedCodes.has(b.code.toUpperCase()) ? 0 : 1;
      if (aMat !== bMat) return aMat - bMat;
      return a.name.localeCompare(b.name);
    });
  }, [countries, materializedCodes, query]);

  /* Enter navigates to the sole remaining result. */
  function handleSearchKeyDown(e) {
    if (e.key === "Enter" && filteredCountries.length === 1) {
      navigate(`/country/${filteredCountries[0].code.toLowerCase()}`);
    }
  }

  return (
    <div className="page page--country-landing container">
      <PageHeader
        eyebrow="COUNTRY INTELLIGENCE"
        title="Country directory"
        description="Browse all 17 monitored markets. Countries with completed briefings appear first."
        meta="17 markets // searchable // keyboard navigable"
      />

      <input
        ref={searchRef}
        className="country-directory-search section-gap"
        type="text"
        placeholder='Search by name or ISO code — press "/" to focus'
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleSearchKeyDown}
      />

      {viewState === "error" ? (
        <section className="section-gap">
          <div className="card state-panel">
            <h2 className="text-headline">Country directory unavailable</h2>
            <p className="text-body text-secondary mt-4">{requestError}</p>
          </div>
        </section>
      ) : null}

      <section className="country-directory-grid section-gap">
        {viewState === "loading" ? (
          Array.from({ length: 17 }).map((_, index) => (
            <div className="country-directory-card" key={`skel-${index}`}>
              <div className="country-directory-card__header">
                <span className="skeleton" style={{ width: "24px", height: "16px", display: "inline-block" }} />
                <span className="skeleton" style={{ width: "64px", height: "16px", borderRadius: "16px" }} />
              </div>
              <div className="country-directory-card__body">
                <div className="skeleton skeleton-title" style={{ width: "60%" }} />
                <div className="skeleton skeleton-text mt-4" style={{ width: "80%" }} />
                <div className="skeleton skeleton-text mt-2" style={{ width: "40%" }} />
              </div>
            </div>
          ))
        ) : (
          filteredCountries.map((country) => {
            const code = country.code.toUpperCase();
            const isMaterialized = materializedCodes.has(code);
            const outlook = outlookByCode[code] ?? null;
            const isOutlookLoading =
              isMaterialized &&
              !outlook &&
              loadingOutlookCodes.includes(code);
            const label = isMaterialized
              ? outlook?.toUpperCase() || "Live"
              : "Pending";
            const tone = isMaterialized ? getOutlookTone(outlook) : "neutral";

            return (
              <Link
                className="country-directory-card"
                key={country.code}
                to={`/country/${country.code.toLowerCase()}`}
              >
                <div className="country-directory-card__header">
                  <span className="flag-frame flag-frame--md">
                    <Flag code={country.code} height="100%" />
                  </span>
                  {isOutlookLoading ? (
                    <span
                      aria-hidden="true"
                      className="skeleton skeleton-pill country-directory-card__status-skeleton"
                    />
                  ) : (
                    <StatusPill tone={tone}>{label}</StatusPill>
                  )}
                </div>
                <div className="country-directory-card__body">
                  <h3 className="text-title">{country.name}</h3>
                  <p className="text-body text-secondary">{country.region}</p>
                  <p className="text-label text-secondary">
                    {country.income_level}
                  </p>
                </div>
              </Link>
            );
          })
        )}
      </section>

      <p className="country-directory-footnote section-gap">
        17-country panel selected for complete 2010-2024 data coverage across
        all six indicators.
      </p>
    </div>
  );
}

export default CountryIntelligenceLanding;
