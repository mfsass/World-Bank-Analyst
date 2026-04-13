import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CountryIntelligenceLanding } from "../src/pages/CountryIntelligenceLanding";
import { CountryIntelligence } from "../src/pages/CountryIntelligence";
import {
  apiRequest,
  fetchCountryDetail,
  fetchGlobalOverview,
} from "../src/api";
import {
  resetCountryDetailCache,
  setCountriesList,
  setOverviewCache,
} from "../src/lib/countryDetailCache";

vi.mock("../src/api", () => {
  return {
    apiRequest: vi.fn(),
    fetchGlobalOverview: vi.fn(),
    fetchCountryDetail: vi.fn(),
  };
});

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver = ResizeObserverMock;

function renderPage(initialEntry = "/country/br") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route element={<CountryIntelligence />} path="/country/:id" />
      </Routes>
    </MemoryRouter>,
  );
}

function renderLandingPage() {
  return render(
    <MemoryRouter initialEntries={["/country"]}>
      <Routes>
        <Route element={<CountryIntelligenceLanding />} path="/country" />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  resetCountryDetailCache();
});

describe("CountryIntelligence", () => {
  it("keeps the directory skeleton until coverage data is ready", async () => {
    let resolveOverview;
    let resolveBrazilBriefing;

    apiRequest.mockResolvedValue([
      { code: "BR", name: "Brazil", region: "Latin America & Caribbean" },
      { code: "US", name: "United States", region: "North America" },
    ]);
    fetchGlobalOverview.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveOverview = () =>
            resolve({
              summary: "Macro dispersion remains high across the monitored set.",
              outlook: "cautious",
              risk_flags: [],
              country_count: 2,
              country_codes: ["BR"],
            });
        }),
    );
    fetchCountryDetail.mockImplementation((code) => {
      if (code === "BR") {
        return new Promise((resolve) => {
          resolveBrazilBriefing = () =>
            resolve({
              code: "BR",
              name: "Brazil",
              region: "Latin America & Caribbean",
              outlook: "cautious",
            });
        });
      }

      return Promise.resolve(null);
    });

    const { container } = renderLandingPage();

    expect(container.querySelectorAll(".country-directory-card").length).toBe(17);
    expect(screen.queryByText("Brazil")).not.toBeInTheDocument();

    resolveOverview();

    const brazilCardTitle = await screen.findByText("Brazil");
    const brazilCard = brazilCardTitle.closest(".country-directory-card");

    expect(brazilCard).not.toBeNull();
    expect(
      brazilCard.querySelector(".country-directory-card__status-skeleton"),
    ).toBeTruthy();
    expect(within(brazilCard).queryByText("CAUTIOUS")).not.toBeInTheDocument();

    resolveBrazilBriefing();

    expect(await within(brazilCard).findByText("CAUTIOUS")).toBeInTheDocument();
  });

  it("keeps the country loading shell visible while the briefing is pending", () => {
    apiRequest.mockImplementation(() => new Promise(() => {}));

    const { container } = renderPage();

    expect(screen.getByRole("heading", { name: "BR" })).toBeInTheDocument();
    expect(screen.getByText("Loading market intelligence…")).toBeInTheDocument();
    expect(screen.getByText("Loading country posture")).toBeInTheDocument();
    expect(container.querySelector(".flag-frame--placeholder")).toBeTruthy();
  });

  it("renders the live market view after the briefing resolves", async () => {
    apiRequest.mockImplementation((path) => {
      if (path === "/countries") {
        return Promise.resolve([
          { code: "BR", name: "Brazil" },
          { code: "US", name: "United States" },
        ]);
      }

      if (path === "/countries/BR") {
        return Promise.resolve({
          code: "BR",
          name: "Brazil",
          region: "Latin America & Caribbean",
          income_level: "Upper middle income",
          source_date_range: "2017:2023",
          outlook: "cautious",
          regime_label: "expansion",
          macro_synthesis:
            "Inflation remains elevated while growth is subdued.",
          risk_flags: ["Inflation pressure persists"],
          indicators: [
            {
              indicator_code: "NY.GDP.MKTP.KD.ZG",
              indicator_name: "GDP growth",
              latest_value: 0.6,
              percent_change: -1.3,
              change_value: -1.3,
              change_basis: "percentage_point",
              signal_polarity: "higher_is_better",
              time_series: [
                { year: 2021, value: 4.8, change_value: 1.4, change_basis: "percentage_point" },
                { year: 2022, value: 1.9, change_value: -2.9, change_basis: "percentage_point" },
                { year: 2023, value: 0.6, change_value: -1.3, change_basis: "percentage_point" },
              ],
              data_year: 2023,
              ai_analysis: "Growth remains subdued.",
              is_anomaly: false,
            },
            {
              indicator_code: "FP.CPI.TOTL.ZG",
              indicator_name: "Inflation",
              latest_value: 6,
              percent_change: 1.1,
              change_value: 1.1,
              change_basis: "percentage_point",
              signal_polarity: "lower_is_better",
              anomaly_basis: "historical",
              time_series: [
                { year: 2021, value: 8.3, change_value: 0.7, change_basis: "percentage_point" },
                { year: 2022, value: 7.1, change_value: -1.2, change_basis: "percentage_point" },
                { year: 2023, value: 6, change_value: -1.1, change_basis: "percentage_point", is_anomaly: true, anomaly_basis: "historical" },
              ],
              data_year: 2023,
              ai_analysis: "Inflation remains above comfort range.",
              is_anomaly: true,
            },
            {
              indicator_code: "SL.UEM.TOTL.ZS",
              indicator_name: "Unemployment",
              latest_value: 32.1,
              percent_change: -0.6,
              change_value: -0.6,
              change_basis: "percentage_point",
              signal_polarity: "lower_is_better",
              time_series: [
                { year: 2021, value: 33.6, change_value: -0.3, change_basis: "percentage_point" },
                { year: 2022, value: 32.7, change_value: -0.9, change_basis: "percentage_point" },
                { year: 2023, value: 32.1, change_value: -0.6, change_basis: "percentage_point" },
              ],
              data_year: 2023,
              ai_analysis: "Labor-market stress remains high.",
              is_anomaly: false,
            },
            {
              indicator_code: "GC.DOD.TOTL.GD.ZS",
              indicator_name: "Government debt",
              latest_value: 74.8,
              percent_change: 3.7,
              change_value: 3.7,
              change_basis: "percentage_point",
              signal_polarity: "lower_is_better",
              time_series: [
                { year: 2021, value: 70.2, change_value: 1.8, change_basis: "percentage_point" },
                { year: 2022, value: 71.1, change_value: 0.9, change_basis: "percentage_point" },
                { year: 2023, value: 74.8, change_value: 3.7, change_basis: "percentage_point" },
              ],
              data_year: 2023,
              ai_analysis: "Debt remains elevated.",
              is_anomaly: false,
            },
          ],
        });
      }

      return Promise.reject(new Error(`Unexpected path: ${path}`));
    });

    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Brazil", level: 1 }),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Inflation remains elevated while growth is subdued."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Macro Intelligence" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Expansion")).toBeInTheDocument();
    expect(screen.getByText("Source window // 2017-2023")).toBeInTheDocument();
    expect(screen.getByText("Latest data year // 2023")).toBeInTheDocument();
    expect(screen.getAllByText("+1.10pp")[0]).toBeInTheDocument();
    expect(screen.getByText("1 anomaly year")).toBeInTheDocument();
    expect(screen.getAllByText("Better when lower").length).toBeGreaterThan(0);
    expect(screen.getByText("Historical anomaly")).toBeInTheDocument();
    expect(screen.getByText("Inflation pressure persists")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "US" })).toBeInTheDocument();
  });

  it("keeps a warm directory visible when the background refresh fails", async () => {
    setCountriesList([
      { code: "BR", name: "Brazil", region: "Latin America & Caribbean" },
      { code: "US", name: "United States", region: "North America" },
    ]);
    setOverviewCache({
      panelOverview: {
        country_codes: ["BR"],
        summary: "Cached monitored-set summary.",
      },
      countries: [
        { code: "BR", name: "Brazil", region: "Latin America & Caribbean" },
        { code: "US", name: "United States", region: "North America" },
      ],
      status: null,
      indicators: [],
    });
    apiRequest.mockRejectedValue(new Error("catalog refresh failed"));
    fetchGlobalOverview.mockRejectedValue(new Error("overview refresh failed"));
    fetchCountryDetail.mockResolvedValue(null);

    renderLandingPage();

    expect(await screen.findByText("Brazil")).toBeInTheDocument();
    expect(
      screen.queryByText("Country directory unavailable"),
    ).not.toBeInTheDocument();
  });
});
