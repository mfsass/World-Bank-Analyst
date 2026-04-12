import Flag from "react-world-flags";
import PropTypes from "prop-types";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  useMapContext,
} from "react-simple-maps";
import { Link } from "react-router-dom";
import worldGeography from "world-atlas/countries-110m.json";

import { AIInsightPanel } from "../components/AIInsightPanel";
import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/PageHeader";
import { StatusPill } from "../components/StatusPill";
import { apiRequest } from "../api";
import {
  deriveCoverageBoard,
  deriveOverviewMetrics,
  derivePressureQueue,
  deriveRegionalBreakdown,
  formatChange,
  formatMetricValue,
  formatSourceDateRange,
  formatTimestamp,
  getEmptyStateBody,
  getEmptyStateHeading,
  getLatestDataYear,
  getOutlookTone,
  getOverviewNarrative,
  getSignalTone,
  getStepSummary,
  getStepTone,
} from "./globalOverviewModel";

const MAP_DIMENSIONS = {
  width: 800,
  height: 420,
};

const MAP_POPOVER = {
  width: 204,
  height: 100,
  gap: 14,
  edgePadding: 12,
};

const MAP_POPOVER_ID = "overview-map-popover";
const QUEUE_CARD_LIMIT = 2;
const QUEUE_PREFETCH_ROOT_MARGIN = "320px 0px";

// 165 fills continents into the canvas with less dead ocean at the poles and edges
const MAP_PROJECTION_CONFIG = {
  scale: 165,
};

// Keep the overview map honest to the active 17-country core panel rather than
// carrying legacy marker positions from superseded country examples.
const COUNTRY_COORDINATES = {
  br: { lat: -15.793889, lon: -47.882778 },
  ca: { lat: 45.4215, lon: -75.6972 },
  gb: { lat: 51.5072, lon: -0.1276 },
  us: { lat: 38.9072, lon: -77.0369 },
  bs: { lat: 25.047984, lon: -77.355413 },
  co: { lat: 4.711, lon: -74.0721 },
  sv: { lat: 13.6929, lon: -89.2182 },
  ge: { lat: 41.6938, lon: 44.8015 },
  hu: { lat: 47.4979, lon: 19.0402 },
  my: { lat: 3.139, lon: 101.6869 },
  nz: { lat: -41.2865, lon: 174.7762 },
  ru: { lat: 55.7558, lon: 37.6173 },
  sg: { lat: 1.3521, lon: 103.8198 },
  es: { lat: 40.4168, lon: -3.7038 },
  ch: { lat: 46.948, lon: 7.4474 },
  tr: { lat: 39.9334, lon: 32.8597 },
  uy: { lat: -34.9011, lon: -56.1645 },
};

const DETAIL_SIGNAL_CODES = [
  "NY.GDP.MKTP.KD.ZG",
  "FP.CPI.TOTL.ZG",
  "SL.UEM.TOTL.ZS",
];

async function fetchCountryBriefing(countryCode) {
  try {
    return await apiRequest(`/countries/${countryCode}`);
  } catch (error) {
    if (error.status === 404) {
      return null;
    }

    throw error;
  }
}

async function fetchGlobalOverview() {
  try {
    return await apiRequest("/overview");
  } catch (error) {
    if (error.status === 404) {
      return null;
    }

    throw error;
  }
}

async function fetchOverviewData() {
  const [status, countries, indicators, panelOverview] = await Promise.all([
    apiRequest("/pipeline/status"),
    apiRequest("/countries"),
    apiRequest("/indicators"),
    fetchGlobalOverview(),
  ]);

  return { status, countries, indicators, briefings: [], panelOverview };
}

function getPipelineTone(status) {
  if (status === "complete") {
    return "success";
  }

  if (status === "running") {
    return "warning";
  }

  if (status === "failed") {
    return "critical";
  }

  return "neutral";
}

function getIndicatorValue(briefing, indicatorCode) {
  return briefing?.indicators?.find(
    (indicator) => indicator.indicator_code === indicatorCode,
  );
}

function getMarkerToneClass(isMaterialised, isSelected) {
  if (isSelected) {
    return "overview-map-marker__dot--selected-core";
  }

  if (!isMaterialised) {
    return "overview-map-marker__dot--pending";
  }

  return "overview-map-marker__dot--materialised";
}

function buildMarketMetrics(briefing) {
  return DETAIL_SIGNAL_CODES.map((indicatorCode) =>
    getIndicatorValue(briefing, indicatorCode),
  ).filter(Boolean);
}

function getCountryCoordinates(countryCode) {
  return COUNTRY_COORDINATES[countryCode?.toLowerCase()] || null;
}

function getMapPopoverPosition(point, bounds) {
  const [x, y] = point;
  const preferredLeft = x - MAP_POPOVER.width / 2;
  const maximumLeft = Math.max(
    MAP_POPOVER.edgePadding,
    bounds.width - MAP_POPOVER.width - MAP_POPOVER.edgePadding,
  );
  const clampedLeft = Math.min(
    maximumLeft,
    Math.max(MAP_POPOVER.edgePadding, preferredLeft),
  );
  const availableAbove = y - MAP_POPOVER.gap - MAP_POPOVER.edgePadding;
  const availableBelow =
    bounds.height - y - MAP_POPOVER.gap - MAP_POPOVER.edgePadding;
  const openBelow =
    availableBelow >= MAP_POPOVER.height || availableBelow >= availableAbove;
  const preferredTop = openBelow
    ? y + MAP_POPOVER.gap
    : y - (MAP_POPOVER.height + MAP_POPOVER.gap);
  const maximumTop = Math.max(
    MAP_POPOVER.edgePadding,
    bounds.height - MAP_POPOVER.height - MAP_POPOVER.edgePadding,
  );
  const clampedTop = Math.min(
    maximumTop,
    Math.max(MAP_POPOVER.edgePadding, preferredTop),
  );

  return {
    left: clampedLeft,
    top: clampedTop,
  };
}

function mergeBriefings(currentBriefings, nextBriefing) {
  const nextBriefingCode = nextBriefing?.code;
  if (!nextBriefingCode) {
    return currentBriefings;
  }

  const currentIndex = currentBriefings.findIndex(
    (briefing) => briefing.code === nextBriefingCode,
  );
  if (currentIndex === -1) {
    return [...currentBriefings, nextBriefing];
  }

  return currentBriefings.map((briefing, index) =>
    index === currentIndex ? nextBriefing : briefing,
  );
}

function useSectionPrefetch(rootMargin = QUEUE_PREFETCH_ROOT_MARGIN) {
  const sectionElementRef = useRef(null);
  const [observedSectionElement, setObservedSectionElement] = useState(null);
  const [isVisible, setIsVisible] = useState(false);

  const sectionRef = useCallback((node) => {
    sectionElementRef.current = node;
    setObservedSectionElement(node);
  }, []);

  useEffect(() => {
    if (isVisible) {
      return undefined;
    }

    if (!observedSectionElement) {
      return undefined;
    }

    if (typeof IntersectionObserver === "undefined") {
      setIsVisible(true);
      return undefined;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin },
    );

    observer.observe(observedSectionElement);
    return () => observer.disconnect();
  }, [isVisible, observedSectionElement, rootMargin]);

  return [sectionRef, sectionElementRef, isVisible];
}

function OverviewLoadingShell({ headerNarrative }) {
  return (
    <div className="page page--overview container">
      <PageHeader
        description={headerNarrative}
        eyebrow="AI-GENERATED OVERVIEW"
        meta="Coverage board // current slice // live-compatible state"
        title="Global Overview"
      />

      <section className="section-gap">
        <div className="ai-insight ai-insight-panel overview-loading-shell">
          <div className="panel-header">
            <div className="overview-loading-shell__hero-copy">
              <p className="text-label">AI monitored-set brief</p>
              <div className="skeleton skeleton-title mt-3 overview-skeleton-title" />
            </div>
            <div className="skeleton skeleton-pill" />
          </div>

          <div className="mt-4">
            <div className="skeleton skeleton-text overview-skeleton-line" />
            <div className="skeleton skeleton-text overview-skeleton-line" />
            <div className="skeleton skeleton-text overview-skeleton-line overview-skeleton-line--short" />
          </div>

          <div className="overview-hero-grid mt-4">
            {Array.from({ length: 3 }).map((_, index) => (
              <article className="card overview-hero-stat" key={`hero-${index}`}>
                <div className="skeleton skeleton-text overview-skeleton-label" />
                <div className="skeleton skeleton-kpi-value mt-3" />
                <div className="skeleton skeleton-text overview-skeleton-line mt-3" />
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="kpi-row section-gap">
        {Array.from({ length: 4 }).map((_, index) => (
          <article className="kpi-card" key={`kpi-${index}`}>
            <div className="skeleton skeleton-text overview-skeleton-label" />
            <div className="skeleton skeleton-kpi-value mt-3" />
            <div className="skeleton skeleton-text overview-skeleton-line--short mt-3" />
          </article>
        ))}
      </section>

      <section className="overview-main-grid section-gap">
        <div className="card overview-panel overview-panel--loading">
          <div className="panel-header">
            <div>
              <p className="text-label">Global risk overview</p>
              <div className="skeleton skeleton-title mt-3 overview-skeleton-panel-title" />
            </div>
          </div>
          <div className="skeleton skeleton-block overview-skeleton-map mt-4" />
        </div>

        <div className="panel-stack">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              className="card overview-panel overview-panel--loading"
              key={`panel-${index}`}
            >
              <div className="panel-header">
                <div>
                  <div className="skeleton skeleton-text overview-skeleton-label" />
                  <div className="skeleton skeleton-title mt-3 overview-skeleton-panel-title" />
                </div>
                <div className="skeleton skeleton-pill" />
              </div>
              <div className="mt-4">
                <div className="skeleton skeleton-text overview-skeleton-line" />
                <div className="skeleton skeleton-text overview-skeleton-line overview-skeleton-line--short" />
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

OverviewLoadingShell.propTypes = {
  headerNarrative: PropTypes.string.isRequired,
};

function OverviewMapLayer({
  countries,
  materialisedCountryCodes,
  selectedMapCountry,
  highlightedMarketCode,
  onToggleMapFocus,
}) {
  const { projection } = useMapContext();
  const materialisedCountryCodeSet = useMemo(
    () => new Set(materialisedCountryCodes),
    [materialisedCountryCodes],
  );

  return (
    <g className="overview-map-surface__interaction-layer">
      {countries.map((country) => {
        const coordinates = getCountryCoordinates(country.code);
        if (!coordinates) {
          return null;
        }

        const [x, y] = projection([coordinates.lon, coordinates.lat]);
        const isMaterialised = materialisedCountryCodeSet.has(country.code);

        return (
          <g key={country.code} transform={`translate(${x} ${y})`}>
            <foreignObject
              className="overview-map-marker__foreign"
              height="28"
              width="28"
              x="-14"
              y="-14"
            >
              <div
                className="overview-map-marker__shell"
                xmlns="http://www.w3.org/1999/xhtml"
              >
                <button
                  aria-controls={
                    country.code === selectedMapCountry
                      ? MAP_POPOVER_ID
                      : undefined
                  }
                  aria-expanded={country.code === selectedMapCountry}
                  aria-label={`Focus ${country.name} market on world map`}
                  className="overview-map-marker"
                  onClick={(e) =>
                    onToggleMapFocus(country.code, e.currentTarget)
                  }
                  type="button"
                >
                  {country.code === selectedMapCountry ? (
                    <span
                      className="overview-map-marker__pulse"
                      aria-hidden="true"
                    />
                  ) : null}
                  <span
                    className={`overview-map-marker__dot${
                      country.code === highlightedMarketCode
                        ? " overview-map-marker__dot--selected"
                        : ""
                    }`}
                    aria-hidden="true"
                  >
                    <span
                      className={`overview-map-marker__dot-core ${getMarkerToneClass(
                        isMaterialised,
                        country.code === highlightedMarketCode,
                      )}`}
                    />
                  </span>
                </button>
              </div>
            </foreignObject>
          </g>
        );
      })}
    </g>
  );
}

// MapPopoverProjection removed — popover position is now computed via DOM
// getBoundingClientRect() on the clicked marker button, which eliminates all
// projection coordinate conversion and DPR scaling issues.

OverviewMapLayer.propTypes = {
  countries: PropTypes.arrayOf(
    PropTypes.shape({
      code: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
    }),
  ).isRequired,
  materialisedCountryCodes: PropTypes.arrayOf(PropTypes.string).isRequired,
  selectedMapCountry: PropTypes.string,
  highlightedMarketCode: PropTypes.string,
  onToggleMapFocus: PropTypes.func.isRequired,
};

export function GlobalOverview() {
  const mapCanvasRef = useRef(null);
  const landingTokenRef = useRef(0);
  const pendingBriefingRequestsRef = useRef(new Map());
  const queuePrefetchStartedRef = useRef(false);
  const [queueSectionRef, queueSectionElementRef, queueSectionVisible] =
    useSectionPrefetch();
  const [overview, setOverview] = useState({
    status: null,
    countries: [],
    indicators: [],
    briefings: [],
  });
  const [viewState, setViewState] = useState("loading");
  const [requestError, setRequestError] = useState("");
  const [selectedMapCountry, setSelectedMapCountry] = useState(null);
  // selectedMarkerRef holds the button element for the active marker so popover
  // position can be computed from real DOM bounds rather than projection math.
  const [selectedMarkerRef, setSelectedMarkerRef] = useState(null);
  const [popoverPosition, setPopoverPosition] = useState(null);
  const [mapBounds, setMapBounds] = useState(MAP_DIMENSIONS);
  const [loadingBriefingCodes, setLoadingBriefingCodes] = useState([]);

  const resetBriefingHydrationState = useCallback(() => {
    landingTokenRef.current += 1;
    pendingBriefingRequestsRef.current.clear();
    queuePrefetchStartedRef.current = false;
    setLoadingBriefingCodes([]);
  }, []);

  const loadCountryBriefing = useCallback(
    async (countryCode) => {
      const nextCountryCode = countryCode?.toUpperCase();
      if (!nextCountryCode) {
        return null;
      }

      const existingBriefing = overview.briefings.find(
        (briefing) => briefing.code === nextCountryCode,
      );
      if (existingBriefing) {
        return existingBriefing;
      }

      const pendingRequest =
        pendingBriefingRequestsRef.current.get(nextCountryCode);
      if (pendingRequest) {
        return pendingRequest;
      }

      const landingToken = landingTokenRef.current;
      setLoadingBriefingCodes((currentCodes) =>
        currentCodes.includes(nextCountryCode)
          ? currentCodes
          : [...currentCodes, nextCountryCode],
      );

      const request = fetchCountryBriefing(nextCountryCode)
        .then((nextBriefing) => {
          if (nextBriefing && landingToken === landingTokenRef.current) {
            setOverview((currentOverview) => ({
              ...currentOverview,
              briefings: mergeBriefings(
                currentOverview.briefings,
                nextBriefing,
              ),
            }));
          }

          return nextBriefing;
        })
        .finally(() => {
          pendingBriefingRequestsRef.current.delete(nextCountryCode);

          if (landingToken === landingTokenRef.current) {
            setLoadingBriefingCodes((currentCodes) =>
              currentCodes.filter((code) => code !== nextCountryCode),
            );
          }
        });

      pendingBriefingRequestsRef.current.set(nextCountryCode, request);
      return request;
    },
    [overview.briefings],
  );

  useEffect(() => {
    let isActive = true;

    async function loadOverview() {
      try {
        const nextOverview = await fetchOverviewData();
        if (!isActive) {
          return;
        }

        resetBriefingHydrationState();
        setOverview(nextOverview);
        setViewState("ready");
        setRequestError("");
      } catch (error) {
        if (!isActive) {
          return;
        }

        setViewState("error");
        setRequestError(error.message);
      }
    }

    loadOverview();

    return () => {
      isActive = false;
    };
  }, [resetBriefingHydrationState]);

  useEffect(() => {
    if (overview.status?.status !== "running") {
      return undefined;
    }

    let isActive = true;
    const intervalId = window.setInterval(async () => {
      try {
        const nextStatus = await apiRequest("/pipeline/status");
        if (!isActive) {
          return;
        }

        setOverview((currentOverview) => ({
          ...currentOverview,
          status: nextStatus,
        }));
        setRequestError("");

        if (nextStatus.status !== "running") {
          window.clearInterval(intervalId);
          const nextOverview = await fetchOverviewData();
          if (!isActive) {
            return;
          }

          resetBriefingHydrationState();
          setOverview(nextOverview);
        }
      } catch (error) {
        if (!isActive) {
          return;
        }

        setRequestError(error.message);
        window.clearInterval(intervalId);
      }
    }, 750);

    return () => {
      isActive = false;
      window.clearInterval(intervalId);
    };
  }, [overview.status?.status, resetBriefingHydrationState]);

  useEffect(() => {
    const canvasElement = mapCanvasRef.current;
    if (!canvasElement) {
      return undefined;
    }

    function updateBounds() {
      const { width, height } = canvasElement.getBoundingClientRect();
      if (width > 0 && height > 0) {
        setMapBounds({ width, height });
      }
    }

    updateBounds();

    if (typeof ResizeObserver === "undefined") {
      return undefined;
    }

    const resizeObserver = new ResizeObserver(() => {
      updateBounds();
    });
    resizeObserver.observe(canvasElement);

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  const briefingByCode = useMemo(
    () =>
      new Map(overview.briefings.map((briefing) => [briefing.code, briefing])),
    [overview.briefings],
  );

  const {
    anomalyCount,
    latestRefresh,
    outlookCounts,
    panelOverview,
    panelSignals,
    materialisedCountries,
    monitoredCountries,
    pipelineStatus,
    pipelineSteps,
    riskLoadedMarkets,
  } = deriveOverviewMetrics(overview);
  const materialisedCountryCodes = useMemo(
    () =>
      panelOverview?.country_codes?.length
        ? panelOverview.country_codes
        : overview.briefings.map((briefing) => briefing.code),
    [overview.briefings, panelOverview],
  );
  const materialisedCountryCodeSet = useMemo(
    () => new Set(materialisedCountryCodes),
    [materialisedCountryCodes],
  );

  const coverageBoard = deriveCoverageBoard(
    overview.countries,
    overview.briefings,
    {
      focusedCode: selectedMapCountry,
      materialisedCountryCodes,
    },
  );
  const regionalBreakdown = deriveRegionalBreakdown(
    overview.countries,
    overview.briefings,
    materialisedCountryCodes,
  );
  const coverageBoardByCode = useMemo(
    () => new Map(coverageBoard.map((market) => [market.code, market])),
    [coverageBoard],
  );
  const pressureQueue = derivePressureQueue(
    overview.countries,
    overview.indicators,
    materialisedCountryCodes,
  );
  const queueMarkets = pressureQueue
    .map(({ code }) => coverageBoardByCode.get(code))
    .filter(Boolean)
    .slice(0, QUEUE_CARD_LIMIT);
  const highlightedMarketCode = selectedMapCountry || null;
  const highlightedMarket =
    highlightedMarketCode && coverageBoardByCode.has(highlightedMarketCode)
      ? coverageBoardByCode.get(highlightedMarketCode)
      : null;
  const highlightedBriefing = highlightedMarketCode
    ? briefingByCode.get(highlightedMarketCode) || null
    : null;
  const highlightedMetrics = buildMarketMetrics(highlightedBriefing);
  const marketOpenHref = highlightedMarket?.href || "/trigger";
  const selectedBriefingLoading = Boolean(
    highlightedMarketCode && loadingBriefingCodes.includes(highlightedMarketCode),
  );
  const hasLoadedCountryPosture = overview.briefings.length > 0;
  const loadedQueueCount = queueMarkets.filter((market) =>
    briefingByCode.has(market.code),
  ).length;
  const queueStatusLabel = queueMarkets.length
    ? loadedQueueCount === queueMarkets.length
      ? "QUEUE READY"
      : queueSectionVisible
        ? `LOADING ${loadedQueueCount}/${queueMarkets.length}`
        : "ON DEMAND"
    : "PENDING";
  const queueStatusTone =
    loadedQueueCount === queueMarkets.length && queueMarkets.length
      ? "success"
      : queueSectionVisible
        ? "warning"
        : "neutral";
  const highlightedStatusTone = highlightedBriefing?.outlook
    ? getOutlookTone(highlightedBriefing.outlook)
    : highlightedMarket?.tone || "neutral";
  const panelOutlookTone = panelOverview?.outlook
    ? getOutlookTone(panelOverview.outlook)
    : getPipelineTone(pipelineStatus);
  const panelStatusLabel = panelOverview?.outlook
    ? panelOverview.outlook.toUpperCase()
    : pipelineStatus.toUpperCase();
  const globalRiskTone =
    !hasLoadedCountryPosture
      ? ""
      : outlookCounts.bearish > 0
      ? " overview-hero-stat--critical"
      : riskLoadedMarkets > 0
        ? ""
        : " overview-hero-stat--success";
  const headerNarrative =
    viewState === "ready"
      ? getOverviewNarrative(
          pipelineStatus,
          monitoredCountries,
          materialisedCountries,
        )
      : viewState === "error"
        ? "The overview could not load from the current slice. Open the trigger flow or retry once the API is reachable."
        : "Loading the current slice so the landing surface reflects live monitored coverage rather than placeholder content.";
  const sourceWindowLabel = formatSourceDateRange(
    panelOverview?.source_date_range,
  );
  const latestDataYear = getLatestDataYear(overview.indicators);
  const latestDataYearLabel = latestDataYear
    ? String(latestDataYear)
    : "Pending";
  const pipelineRefreshLabel = latestRefresh
    ? formatTimestamp(latestRefresh)
    : "Pending";
  const queueLeadCopy =
    queueMarkets.length > 0
      ? "Load the live queue below or focus a market on the map when you want a country briefing."
      : "Country drilldowns will appear once the monitored-set queue is available.";
  const riskLoadedValue = hasLoadedCountryPosture ? riskLoadedMarkets : "--";

  const sharedActions = (
    <div className="button-row">
      <Link className="btn-primary" to="/trigger">
        {pipelineStatus === "running" ? "Monitor pipeline" : "Open pipeline"}
      </Link>
      {selectedMapCountry ? (
        <Link className="btn-ghost" to={marketOpenHref}>
          Open selected country
        </Link>
      ) : (
        <button
          className="btn-ghost"
          onClick={() =>
            queueSectionElementRef.current?.scrollIntoView({
              behavior: "smooth",
              block: "start",
            })
          }
          type="button"
        >
          Review country queue
        </button>
      )}
    </div>
  );

  function toggleMapFocus(countryCode, element) {
    const isDeselect = countryCode === selectedMapCountry;
    setSelectedMapCountry(isDeselect ? null : countryCode);
    setSelectedMarkerRef(isDeselect ? null : element || null);

    if (!isDeselect && materialisedCountryCodeSet.has(countryCode)) {
      void loadCountryBriefing(countryCode);
    }
  }

  useEffect(() => {
    if (
      viewState !== "ready" ||
      !queueSectionVisible ||
      queuePrefetchStartedRef.current ||
      !queueMarkets.length
    ) {
      return;
    }

    queuePrefetchStartedRef.current = true;
    void Promise.all(queueMarkets.map((market) => loadCountryBriefing(market.code)));
  }, [loadCountryBriefing, queueMarkets, queueSectionVisible, viewState]);

  // Derive popover position from the marker button's actual DOM bounds.
  // mapBounds is used as a resize trigger — when the canvas resizes, this effect
  // re-fires and reads fresh getBoundingClientRect() values so placement stays
  // accurate at any container width without any projection math.
  useEffect(() => {
    if (!selectedMarkerRef || !mapCanvasRef.current) {
      setPopoverPosition(null);
      return;
    }
    const canvasRect = mapCanvasRef.current.getBoundingClientRect();
    const markerRect = selectedMarkerRef.getBoundingClientRect();
    const cx = markerRect.left + markerRect.width / 2 - canvasRect.left;
    const cy = markerRect.top + markerRect.height / 2 - canvasRect.top;
    setPopoverPosition(
      getMapPopoverPosition([cx, cy], {
        width: canvasRect.width,
        height: canvasRect.height,
      }),
    );
  }, [selectedMarkerRef, mapBounds]);

  if (viewState === "loading") {
    return <OverviewLoadingShell headerNarrative={headerNarrative} />;
  }

  if (viewState === "error") {
    return (
      <div className="page page--overview container">
        <PageHeader
          actions={sharedActions}
          description={headerNarrative}
          eyebrow="AI-GENERATED OVERVIEW"
          meta="Coverage board // current slice // live-compatible state"
          title="Global Overview"
        />

        <section className="section-gap">
          <div className="card state-panel">
            <p className="text-label">Overview unavailable</p>
            <h2 className="text-headline mt-3">
              The landing page could not hydrate
            </h2>
            <p className="text-body text-secondary mt-4">{requestError}</p>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="page page--overview container">
      <PageHeader
        actions={sharedActions}
        description={headerNarrative}
        eyebrow="AI-GENERATED OVERVIEW"
        meta={`Source window // ${sourceWindowLabel} · Latest data year // ${latestDataYearLabel} · Pipeline refresh // ${pipelineRefreshLabel}`}
        title="Global Overview"
      />

      <section className="section-gap">
        <AIInsightPanel
          eyebrow="AI monitored-set brief"
          footer={
            <div className="overview-hero-footer">
              <span className="text-label">
                Source window // {sourceWindowLabel}
              </span>
              <span className="text-label">
                Live briefings // {materialisedCountries}/{monitoredCountries}
              </span>
              <span className="text-label">
                Drilldown // {selectedMapCountry || "Select market"}
              </span>
            </div>
          }
          status={panelStatusLabel}
          title="Monitored-set operating picture"
          tone={panelOutlookTone}
        >
          <p className="text-body">
            {panelOverview?.summary || headerNarrative}
          </p>
          {panelOverview?.risk_flags?.length ? (
            <div className="overview-signal-list mt-4">
              {panelOverview.risk_flags.slice(0, 2).map((riskFlag, index) => (
                <article
                  className="overview-signal-card"
                  key={`${riskFlag}-${index}`}
                >
                  <p className="text-label">Cross-market flag {index + 1}</p>
                  <p className="text-body text-secondary mt-3">{riskFlag}</p>
                </article>
              ))}
            </div>
          ) : null}
          <div className="overview-hero-grid mt-4">
            <article
              className={`card overview-hero-stat${materialisedCountries > 0 ? " overview-hero-stat--success" : ""}`}
            >
              <span className="text-label">Coverage</span>
              <span className="overview-hero-stat__value">
                {materialisedCountries}/{monitoredCountries}
              </span>
              <p className="overview-hero-stat__desc text-body text-secondary">
                Live briefings confirmed in the active monitored set.
              </p>
            </article>
            <article
              className={`card overview-hero-stat${anomalyCount > 0 ? " overview-hero-stat--critical" : " overview-hero-stat--success"}`}
            >
              <span className="text-label">Signal pressure</span>
              <span className="overview-hero-stat__value">{anomalyCount}</span>
              <p className="overview-hero-stat__desc text-body text-secondary">
                Indicator anomalies flagged in the latest pool.
              </p>
            </article>
            <article className={`card overview-hero-stat${globalRiskTone}`}>
              <span className="text-label">Risk-loaded markets</span>
              <span className="overview-hero-stat__value">
                {riskLoadedValue}
              </span>
              <p className="overview-hero-stat__desc text-body text-secondary">
                {hasLoadedCountryPosture
                  ? outlookCounts.bearish > 0
                    ? `${outlookCounts.bearish} bearish and ${outlookCounts.cautious} cautious markets are shaping the panel view.`
                    : riskLoadedMarkets > 0
                      ? `${outlookCounts.cautious} cautious markets are shaping the panel view.`
                      : "No bearish or cautious market outlooks are currently materialised."
                  : "Country posture stays on demand until you focus a market or load the queue below."}
              </p>
            </article>
          </div>
        </AIInsightPanel>
      </section>

      {anomalyCount > 0 ? (
        <section className="section-gap">
          <div className="anomaly-banner">
            <div className="anomaly-banner__content">
              <span className="material-symbols-outlined anomaly-banner__icon">
                warning
              </span>
              <span>
                {anomalyCount} anomalies flagged across the current indicator
                set
              </span>
            </div>
            <Link className="anomaly-banner__action" to="/trigger">
              Review pipeline
            </Link>
          </div>
        </section>
      ) : null}

      <section className="kpi-row section-gap" aria-live="polite">
        <KpiCard
          freshness={
            overview.status?.started_at
              ? `PIPELINE REFRESH ${formatTimestamp(
                  overview.status.completed_at || overview.status.started_at,
                )}`
              : "AWAITING FIRST RUN"
          }
          label="Pipeline Status"
          status={pipelineStatus.toUpperCase()}
          statusTone={getStepTone(pipelineStatus)}
          value={pipelineStatus.toUpperCase()}
        />
        <KpiCard
          freshness={`${monitoredCountries} MONITORED IN CURRENT SCOPE`}
          label="Countries Materialised"
          status={`${materialisedCountries}/${monitoredCountries}`}
          statusTone={materialisedCountries > 0 ? "success" : "neutral"}
          value={materialisedCountries}
        />
        <KpiCard
          freshness={
            sourceWindowLabel !== "Pending"
              ? `SOURCE WINDOW ${sourceWindowLabel}`
              : "SOURCE WINDOW PENDING"
          }
          label="Indicators Analysed"
          status={`${overview.indicators.length} ROWS`}
          statusTone={overview.indicators.length > 0 ? "success" : "neutral"}
          value={overview.indicators.length}
        />
        <KpiCard
          freshness={
            queueSectionVisible
              ? "COUNTRY QUEUE HYDRATING"
              : "COUNTRY DETAIL LOADS ON DEMAND"
          }
          label="Country Queue"
          status={queueStatusLabel}
          statusTone={queueStatusTone}
          value={queueMarkets.length ? `${loadedQueueCount}/${queueMarkets.length}` : "0/0"}
        />
      </section>

      <section className="overview-main-grid section-gap">
        <div className="card overview-panel">
          <div className="panel-header">
            <div>
              <p className="text-label">Global risk overview</p>
              <h2 className="text-headline mt-3">Monitored markets</h2>
            </div>
            <StatusPill tone="neutral">Current slice</StatusPill>
          </div>
          <div className="overview-map-surface mt-4">
            <div
              aria-label="World coverage map"
              className="overview-map-surface__canvas"
              ref={mapCanvasRef}
              role="group"
            >
              <ComposableMap
                className="overview-map-surface__svg"
                height={MAP_DIMENSIONS.height}
                projection="geoEqualEarth"
                projectionConfig={MAP_PROJECTION_CONFIG}
                width={MAP_DIMENSIONS.width}
              >
                <Geographies geography={worldGeography}>
                  {({ geographies }) =>
                    geographies.map((geography) => (
                      <Geography
                        className="overview-map-surface__land"
                        geography={geography}
                        key={geography.rsmKey}
                        tabIndex={-1}
                      />
                    ))
                  }
                </Geographies>
                <OverviewMapLayer
                  countries={overview.countries}
                  highlightedMarketCode={highlightedMarketCode}
                  materialisedCountryCodes={materialisedCountryCodes}
                  onToggleMapFocus={toggleMapFocus}
                  selectedMapCountry={selectedMapCountry}
                />
              </ComposableMap>

              {selectedMapCountry && highlightedMarket && popoverPosition ? (
                <div
                  className="overview-map-popover-anchor"
                  style={{
                    left: `${popoverPosition.left}px`,
                    top: `${popoverPosition.top}px`,
                  }}
                >
                  <div
                    aria-label={`${highlightedMarket.name} market actions`}
                    aria-live="polite"
                    className="overview-map-popover"
                    id={MAP_POPOVER_ID}
                    role="region"
                  >
                    <div className="overview-map-popover__topbar">
                      <span className="flag-frame flag-frame--sm overview-map-popover__flag">
                        <Flag code={highlightedMarket.code} height="100%" />
                      </span>
                      <span className="overview-map-popover__status">
                        {highlightedBriefing?.outlook
                          ? highlightedBriefing.outlook.toUpperCase()
                          : highlightedMarket.statusLabel}
                      </span>
                    </div>

                    <div className="overview-map-popover__body">
                      <div className="overview-map-popover__title">
                        <span className="overview-map-popover__name">
                          {highlightedMarket.name}
                        </span>
                        <span className="text-label text-secondary">
                          {highlightedMarket.region}
                        </span>
                      </div>
                    </div>

                    <Link
                      className="btn-ghost overview-map-popover__link"
                      to={marketOpenHref}
                    >
                      Open intelligence
                    </Link>
                  </div>
                </div>
              ) : null}
            </div>

            <div className="overview-market-command-list mt-4" role="list">
              {coverageBoard.map((market) => (
                <button
                  className={`overview-market-command${
                    market.code === highlightedMarketCode
                      ? " overview-market-command--active"
                      : ""
                  }`}
                  key={market.code}
                  onClick={() => toggleMapFocus(market.code)}
                  type="button"
                >
                  <span className="overview-market-command__code">
                    {market.code}
                  </span>
                  <span className="overview-market-command__status">
                    {market.isMaterialised ? "Live" : "Pending"}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="panel-stack">
          <div className="card overview-panel">
            <div className="panel-header">
              <div>
                <p className="text-label">Country drilldown</p>
                <h2 className="text-headline mt-3">Country drilldown</h2>
              </div>
              <StatusPill tone={highlightedMarket?.tone || "neutral"}>
                {highlightedMarket?.statusLabel || "Pending"}
              </StatusPill>
            </div>
            {!highlightedMarket ? (
              <>
                <div
                  className="overview-context-market overview-context-market--empty mt-4"
                  aria-live="polite"
                >
                  <div>
                    <p className="text-label">Panel-first landing</p>
                    <h3 className="text-title mt-3">No market preselected</h3>
                    <p className="text-body text-secondary mt-3">
                      The landing page stays global until you focus a market on
                      the map or open the drilldown queue below.
                    </p>
                  </div>
                  <StatusPill tone="neutral">ON DEMAND</StatusPill>
                </div>

                <p className="text-body text-secondary mt-4 overview-market-summary">
                  {queueLeadCopy}
                </p>

                <div className="button-row mt-4">
                  <button
                    className="btn-ghost"
                    onClick={() =>
                      queueSectionElementRef.current?.scrollIntoView({
                        behavior: "smooth",
                        block: "start",
                      })
                    }
                    type="button"
                  >
                    Open drilldown queue
                  </button>
                </div>
              </>
            ) : (
              <>
                <div
                  className="overview-context-market mt-4"
                  aria-live="polite"
                >
                  <span className="flag-frame flag-frame--md">
                    <Flag code={highlightedMarket.code} height="100%" />
                  </span>
                  <div>
                    <p className="text-label">Focused market</p>
                    <h3 className="text-title mt-3">
                      {highlightedMarket.name}
                    </h3>
                    <p className="text-body text-secondary mt-3">
                      {highlightedMarket.region}
                    </p>
                  </div>
                  <StatusPill tone={highlightedStatusTone}>
                    {selectedBriefingLoading
                      ? "LOADING"
                      : highlightedBriefing?.outlook
                        ? highlightedBriefing.outlook.toUpperCase()
                        : highlightedMarket.statusLabel}
                  </StatusPill>
                </div>

                {selectedBriefingLoading ? (
                  <div className="overview-drilldown-loading mt-4">
                    <div className="skeleton skeleton-text overview-skeleton-line" />
                    <div className="skeleton skeleton-text overview-skeleton-line" />
                    <div className="overview-market-metrics mt-4">
                      {Array.from({ length: 3 }).map((_, index) => (
                        <article
                          className="overview-market-metric overview-market-metric--loading"
                          key={`metric-skeleton-${index}`}
                        >
                          <div className="skeleton skeleton-text overview-skeleton-label" />
                          <div className="skeleton skeleton-kpi-value mt-3" />
                          <div className="skeleton skeleton-text overview-skeleton-line--short mt-3" />
                        </article>
                      ))}
                    </div>
                  </div>
                ) : (
                  <>
                    <p className="text-body text-secondary mt-4 overview-market-summary">
                      {highlightedBriefing?.macro_synthesis ||
                        highlightedMarket.summary}
                    </p>

                    {highlightedMetrics.length ? (
                      <div className="overview-market-metrics mt-4">
                        {highlightedMetrics.map((indicator) => (
                          <article
                            className="overview-market-metric"
                            key={indicator.indicator_code}
                          >
                            <span className="text-label">
                              {indicator.indicator_name}
                            </span>
                            <span className="text-metric mt-3">
                              {formatMetricValue(
                                indicator.indicator_code,
                                indicator.latest_value,
                              )}
                            </span>
                            <span
                              className={`text-label mt-3 ${getSignalTone(
                                indicator.indicator_code,
                                indicator.percent_change,
                              )}`}
                            >
                              {formatChange(indicator.percent_change)}
                            </span>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p className="text-body text-secondary mt-4">
                        {highlightedMarket.isMaterialised
                          ? "The country briefing is still hydrating for this market."
                          : "No live signal pack is materialised for this market yet."}
                      </p>
                    )}
                  </>
                )}

                <div className="button-row mt-4">
                  <Link className="btn-ghost" to={marketOpenHref}>
                    Open market
                  </Link>
                  <button
                    className="shell-command-link"
                    onClick={() => {
                      setSelectedMapCountry(null);
                      setSelectedMarkerRef(null);
                    }}
                    type="button"
                  >
                    Reset focus
                  </button>
                </div>
              </>
            )}
          </div>

          <div className="card overview-panel">
            <div className="panel-header">
              <div>
                <p className="text-label">Current slice</p>
                <h2 className="text-headline mt-3">Pipeline state</h2>
              </div>
              <StatusPill tone={getPipelineTone(pipelineStatus)}>
                {pipelineStatus.toUpperCase()}
              </StatusPill>
            </div>
            <div className="overview-step-list mt-4">
              {pipelineSteps.map((step) => (
                <article className="overview-step-card" key={step.name}>
                  <div className="panel-header">
                    <span className="text-label">{step.name}</span>
                    <StatusPill tone={getStepTone(step.status)}>
                      {step.status.toUpperCase()}
                    </StatusPill>
                  </div>
                  <p className="text-body text-secondary mt-3">
                    {getStepSummary(step)}
                  </p>
                </article>
              ))}
            </div>
          </div>

          <div className="card overview-panel">
            <div className="panel-header">
              <div>
                <p className="text-label">Regional breakdown</p>
                <h2 className="text-headline mt-3">Coverage by region</h2>
              </div>
              <StatusPill tone="neutral">Live coverage</StatusPill>
            </div>
            <div className="overview-region-list mt-4">
              {regionalBreakdown.map((region) => (
                <article className="overview-region-card" key={region.region}>
                  <div className="panel-header">
                    <div>
                      <h3 className="text-title">{region.region}</h3>
                      <p className="text-body text-secondary mt-3">
                        {region.summary}
                      </p>
                    </div>
                    <StatusPill tone={region.tone}>
                      {region.materialisedCount > 0 ? "Live" : "Pending"}
                    </StatusPill>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="section-gap" ref={queueSectionRef}>
        <div className="panel-header">
          <div>
            <p className="text-label">Country intelligence feed</p>
            <h2 className="text-headline mt-3">
              Panel pressure and drilldown queue
            </h2>
          </div>
          <StatusPill tone={queueStatusTone}>{queueStatusLabel}</StatusPill>
        </div>
        <div className="overview-depth-grid mt-4">
          {queueMarkets.map((market, index) => {
            const briefing = briefingByCode.get(market.code);
            const isLoading = loadingBriefingCodes.includes(market.code);
            const leadIndicator = briefing
              ? getIndicatorValue(briefing, "NY.GDP.MKTP.KD.ZG") ||
                getIndicatorValue(briefing, "FP.CPI.TOTL.ZG")
              : null;

            if (!briefing) {
              return (
                <article
                  className="market-card market-card--loading"
                  key={market.code}
                >
                  <div className="market-card__header">
                    <div>
                      <p className="market-card__node-id">
                        NODE-{String(index + 1).padStart(3, "0")}
                      </p>
                      <div className="market-card__title-row mt-3">
                        <span className="flag-frame flag-frame--sm market-card__flag">
                          <Flag code={market.code} height="100%" />
                        </span>
                        <h3 className="market-card__country">{market.name}</h3>
                      </div>
                    </div>
                    <StatusPill tone={isLoading ? "warning" : "neutral"}>
                      {isLoading ? "LOADING" : market.statusLabel}
                    </StatusPill>
                  </div>
                  <div className="mt-4">
                    <div className="skeleton skeleton-text overview-skeleton-line" />
                    <div className="skeleton skeleton-text overview-skeleton-line" />
                  </div>
                  <div className="market-card__meta mt-4">
                    <span>{market.region}</span>
                    <span>
                      {isLoading ? "Hydrating live briefing" : "Awaiting briefing"}
                    </span>
                  </div>
                </article>
              );
            }

            return (
              <Link className="market-card" key={market.code} to={market.href}>
                <div className="market-card__header">
                  <div>
                    <p className="market-card__node-id">
                      NODE-{String(index + 1).padStart(3, "0")}
                    </p>
                    <div className="market-card__title-row mt-3">
                      <span className="flag-frame flag-frame--sm market-card__flag">
                        <Flag code={market.code} height="100%" />
                      </span>
                      <h3 className="market-card__country">{market.name}</h3>
                    </div>
                  </div>
                  <StatusPill tone={market.tone}>
                    {briefing.outlook
                      ? briefing.outlook.toUpperCase()
                      : market.statusLabel}
                  </StatusPill>
                </div>
                <p className="market-card__insight mt-4">
                  {briefing.macro_synthesis}
                </p>
                <div className="market-card__meta mt-4">
                  <span>{market.region}</span>
                  <span>
                    {leadIndicator
                      ? `${formatMetricValue(
                          leadIndicator.indicator_code,
                          leadIndicator.latest_value,
                        )} // ${formatChange(leadIndicator.percent_change)}`
                      : "Awaiting briefing"}
                  </span>
                </div>
              </Link>
            );
          })}

          {panelSignals[0] ? (
            <article className="card overview-depth-card">
              <p className="text-label">Panel signal pack</p>
              <div className="overview-signal-list mt-4">
                {panelSignals.slice(0, 2).map((indicator) => (
                  <div
                    className="overview-signal-card"
                    key={indicator.indicator_code}
                  >
                    <div className="panel-header">
                      <h3 className="text-title">{indicator.indicator_name}</h3>
                      {indicator.anomalyCount > 0 ? (
                        <StatusPill tone="critical">Anomaly</StatusPill>
                      ) : null}
                    </div>
                    <div className="indicator-meta mt-3">
                      <span className="text-metric">{`${indicator.adverseCount}/${indicator.coverageCount}`}</span>
                      <span className={`text-label ${indicator.tone}`}>
                        {indicator.anomalyCount > 0
                          ? `${indicator.anomalyCount} anomalies`
                          : "No anomalies"}
                      </span>
                    </div>
                    <p className="text-body text-secondary mt-3">
                      {indicator.stressedMarketCode
                        ? `${indicator.adverseCount} of ${indicator.coverageCount} markets moved in the wrong direction. Current stress point // ${indicator.stressedMarketCode} ${formatChange(indicator.stressedMarketChange)}`
                        : `${indicator.adverseCount} of ${indicator.coverageCount} markets moved in the wrong direction.`}
                    </p>
                  </div>
                ))}
              </div>
            </article>
          ) : (
            <article className="card overview-depth-card">
              <p className="text-label">Panel signal pack</p>
              <h3 className="text-headline mt-3">
                {getEmptyStateHeading(pipelineStatus)}
              </h3>
              <p className="text-body text-secondary mt-4">
                {getEmptyStateBody(pipelineStatus)}
              </p>
            </article>
          )}
        </div>
      </section>
    </div>
  );
}
export default GlobalOverview;
