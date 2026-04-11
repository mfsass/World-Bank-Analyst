import assert from "node:assert/strict";
import test from "node:test";

import {
  deriveCoverageBoard,
  deriveRegionalBreakdown,
  deriveOverviewMetrics,
  getOutlookTone,
  getSignalTone,
} from "../src/pages/globalOverviewModel.js";

test("overview mapping counts only confirmed briefings and applies finance tones", () => {
  const overview = {
    status: { status: "complete", completed_at: "2026-04-08T19:19:34Z" },
    countries: [{ code: "ZA" }, { code: "KE" }],
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
  assert.equal(metrics.materialisedCountries, 1);
  assert.equal(metrics.featuredCountry?.code, "ZA");
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
      { code: "DE", outlook: "bullish" },
    ],
  );

  assert.equal(regions[0].region, "Sub-Saharan Africa");
  assert.equal(regions[0].monitoredCount, 2);
  assert.equal(regions[0].materialisedCount, 1);
  assert.equal(regions[0].tone, "warning");
  assert.equal(regions[0].summary, "1/2 live briefings");
  assert.equal(regions[1].region, "Europe & Central Asia");
  assert.equal(regions[1].tone, "success");
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
      { code: "DE", outlook: "bullish" },
    ],
    "ZA",
  );

  assert.equal(markets.length, 3);
  assert.equal(markets[0].code, "ZA");
  assert.equal(markets[0].statusLabel, "Live");
  assert.equal(markets[0].tone, "warning");
  assert.equal(markets[0].isFeatured, true);
  assert.equal(markets[1].statusLabel, "Pending");
  assert.equal(markets[1].tone, "neutral");
  assert.equal(markets[2].href, "/country/de");
});
