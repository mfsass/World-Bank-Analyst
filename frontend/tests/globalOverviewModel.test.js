import assert from "node:assert/strict";
import test from "node:test";

import {
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
