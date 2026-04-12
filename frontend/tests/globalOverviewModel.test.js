import assert from "node:assert/strict";
import test from "node:test";

import {
  deriveCoverageBoard,
  deriveRegionalBreakdown,
  deriveOverviewMetrics,
  derivePressureQueue,
  derivePressureWatchlist,
  formatSourceDateRange,
  getLatestDataYear,
  getOutlookTone,
  getPanelSignals,
  getSignalTone,
} from "../src/pages/globalOverviewModel.js";

test("overview mapping uses the stored panel coverage set and applies finance tones", () => {
  const overview = {
    status: { status: "complete", completed_at: "2026-04-08T19:19:34Z" },
    countries: [{ code: "ZA" }, { code: "KE" }],
    panelOverview: { country_codes: ["ZA", "KE"] },
    indicators: [
      {
        country_code: "ZA",
        indicator_code: "FP.CPI.TOTL.ZG",
        is_anomaly: true,
        updated_at: "2026-04-08T19:19:34Z",
      },
      {
        country_code: "KE",
        indicator_code: "NY.GDP.MKTP.KD.ZG",
        is_anomaly: false,
        updated_at: "2026-04-08T19:19:34Z",
      },
    ],
    briefings: [
      {
        code: "ZA",
        outlook: "cautious",
        indicators: [
          {
            indicator_code: "FP.CPI.TOTL.ZG",
            percent_change: 2.5,
          },
        ],
      },
    ],
  };

  const metrics = deriveOverviewMetrics(overview);

  assert.equal(metrics.monitoredCountries, 2);
  assert.equal(metrics.materialisedCountries, 2);
  assert.equal(metrics.riskLoadedMarkets, 1);
  assert.equal(getSignalTone("FP.CPI.TOTL.ZG", 2.5), "text-critical");
  assert.equal(getSignalTone("GC.DOD.TOTL.GD.ZS", -1.2), "text-success");
  assert.equal(getOutlookTone("cautious"), "warning");
  assert.equal(getOutlookTone("bearish"), "critical");
});

test("regional breakdown reports monitored and materialised coverage by region", () => {
  const regions = deriveRegionalBreakdown(
    [
      { code: "ZA", region: "Sub-Saharan Africa" },
      { code: "NG", region: "Sub-Saharan Africa" },
      { code: "DE", region: "Europe & Central Asia" },
    ],
    [
      { code: "ZA", outlook: "cautious" },
    ],
    ["ZA", "DE"],
  );

  assert.equal(regions[0].region, "Sub-Saharan Africa");
  assert.equal(regions[0].monitoredCount, 2);
  assert.equal(regions[0].materialisedCount, 1);
  assert.equal(regions[0].tone, "warning");
  assert.equal(regions[0].summary, "1/2 live briefings");
  assert.equal(regions[1].region, "Europe & Central Asia");
  assert.equal(regions[1].materialisedCount, 1);
  assert.equal(regions[1].tone, "neutral");
});

test("coverage board retains every monitored market without fabricating map state", () => {
  const markets = deriveCoverageBoard(
    [
      { code: "ZA", name: "South Africa", region: "Sub-Saharan Africa" },
      { code: "NG", name: "Nigeria", region: "Sub-Saharan Africa" },
      { code: "DE", name: "Germany", region: "Europe & Central Asia" },
    ],
    [
      { code: "ZA", outlook: "cautious" },
    ],
    {
      focusedCode: "ZA",
      materialisedCountryCodes: ["ZA", "DE"],
    },
  );

  assert.equal(markets.length, 3);
  assert.equal(markets[0].code, "ZA");
  assert.equal(markets[0].statusLabel, "Live");
  assert.equal(markets[0].tone, "warning");
  assert.equal(markets[0].isFocused, true);
  assert.equal(markets[1].statusLabel, "Pending");
  assert.equal(markets[1].tone, "neutral");
  assert.equal(markets[2].statusLabel, "Live");
  assert.equal(markets[2].href, "/country/de");
});

test("pressure queue prioritises live markets before pending ones", () => {
  const queue = derivePressureQueue(
    [
      { code: "ZA" },
      { code: "NG" },
      { code: "DE" },
    ],
    [
      {
        country_code: "ZA",
        indicator_code: "FP.CPI.TOTL.ZG",
        percent_change: 1.8,
        is_anomaly: false,
      },
      {
        country_code: "NG",
        indicator_code: "FP.CPI.TOTL.ZG",
        percent_change: 4.2,
        is_anomaly: true,
      },
    ],
    ["ZA", "DE"],
  );

  assert.deepEqual(
    queue.map((market) => market.code),
    ["ZA", "DE", "NG"],
  );
});

test("source-window helpers keep freshness copy honest", () => {
  assert.equal(formatSourceDateRange("2010:2024"), "2010-2024");
  assert.equal(
    getLatestDataYear([{ data_year: 2023 }, { data_year: 2024 }, {}]),
    2024,
  );
});

test("panel signals keep adverse moves separate from statistical anomalies", () => {
  const signals = getPanelSignals([
    {
      country_code: "BR",
      indicator_code: "NY.GDP.MKTP.KD.ZG",
      indicator_name: "GDP growth (annual %)",
      percent_change: -1.3,
      is_anomaly: false,
    },
    {
      country_code: "US",
      indicator_code: "NY.GDP.MKTP.KD.ZG",
      indicator_name: "GDP growth (annual %)",
      percent_change: 0.8,
      is_anomaly: false,
    },
  ]);

  assert.equal(signals.length, 1);
  assert.equal(signals[0].adverseCount, 1);
  assert.equal(signals[0].anomalyCount, 0);
  assert.equal(signals[0].statisticalAnomalyLabel, "0 statistical anomalies");
  assert.equal(signals[0].statisticalAnomalyTone, "text-secondary");
});

test("pressure watchlist exposes live markets first with lead stress indicators", () => {
  const watchlist = derivePressureWatchlist(
    [
      {
        code: "BR",
        name: "Brazil",
        region: "Latin America & Caribbean",
      },
      {
        code: "US",
        name: "United States",
        region: "North America",
      },
      {
        code: "NG",
        name: "Nigeria",
        region: "Sub-Saharan Africa",
      },
    ],
    [
      {
        code: "BR",
        outlook: "cautious",
        macro_synthesis: "Growth remains weak while inflation pressure persists.",
      },
    ],
    [
      {
        country_code: "BR",
        indicator_code: "NY.GDP.MKTP.KD.ZG",
        indicator_name: "GDP growth (annual %)",
        percent_change: -1.3,
        is_anomaly: false,
      },
      {
        country_code: "US",
        indicator_code: "NY.GDP.MKTP.KD.ZG",
        indicator_name: "GDP growth (annual %)",
        percent_change: 0.8,
        is_anomaly: false,
      },
      {
        country_code: "NG",
        indicator_code: "FP.CPI.TOTL.ZG",
        indicator_name: "Inflation, consumer prices (annual %)",
        percent_change: 4.2,
        is_anomaly: true,
      },
    ],
    ["BR", "US"],
    3,
  );

  assert.deepEqual(
    watchlist.map((market) => market.code),
    ["BR", "US", "NG"],
  );
  assert.equal(watchlist[0].statusLabel, "CAUTIOUS");
  assert.equal(watchlist[0].leadIndicatorCode, "NY.GDP.MKTP.KD.ZG");
  assert.equal(watchlist[0].leadChange, -1.3);
  assert.equal(
    watchlist[0].summary,
    "Growth remains weak while inflation pressure persists.",
  );
  assert.equal(watchlist[2].statusLabel, "PENDING");
});
