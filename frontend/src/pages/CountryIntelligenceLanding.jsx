import Flag from "react-world-flags";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { StatusPill } from "../components/StatusPill";
import { apiRequest, fetchCountryDetail } from "../api";
import {
  setCachedCountry,
  setCountriesList,
  startBackgroundWarm,
} from "../lib/countryDetailCache";
import { getOutlookTone } from "./globalOverviewModel";

export function CountryIntelligenceLanding() {
  const [countries, setCountries] = useState([]);
  const [materializedCodes, setMaterializedCodes] = useState(new Set());
  const [outlookByCode, setOutlookByCode] = useState({});
  const [query, setQuery] = useState("");
  const searchRef = useRef(null);
  const navigate = useNavigate();

  /* Fetch the country catalog and overview (materialized codes) on mount. */
  useEffect(() => {
    apiRequest("/countries")
      .then((countriesList) => {
        setCountries(countriesList);
        // Persist the list so the market switcher on /country/:id is instant.
        setCountriesList(countriesList);
        // Warm all monitored countries in the background after the catalog
        // loads. Already-cached codes are skipped automatically, so this is
        // safe to call unconditionally even when the user navigates away.
        startBackgroundWarm(
          countriesList.map((c) => c.code),
          fetchCountryDetail,
        );
      })
      .catch(() => {});

    apiRequest("/overview")
      .then((overview) => {
        const codes = overview?.country_codes ?? [];
        setMaterializedCodes(new Set(codes.map((c) => c.toUpperCase())));

        /* Fetch briefings for materialized countries to get outlook.
         * Results are also stored in the shared cache so /country/:id can
         * skip its loading state for any market the user is about to visit. */
        codes.forEach((code) => {
          fetchCountryDetail(code)
            .then((briefing) => {
              if (!briefing) return;
              setOutlookByCode((prev) => ({
                ...prev,
                [code.toUpperCase()]: briefing?.outlook ?? null,
              }));
              setCachedCountry(code, briefing);
            })
            .catch(() => {});
        });
      })
      .catch(() => {});
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

      <section className="country-directory-grid section-gap">
        {filteredCountries.map((country) => {
          const code = country.code.toUpperCase();
          const isMaterialized = materializedCodes.has(code);
          const outlook = outlookByCode[code];
          const tone = isMaterialized ? getOutlookTone(outlook) : "neutral";
          const label = isMaterialized ? (outlook ?? "Processed") : "Pending";

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
                <StatusPill tone={tone}>{label}</StatusPill>
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
        })}
      </section>
    </div>
  );
}

export default CountryIntelligenceLanding;
