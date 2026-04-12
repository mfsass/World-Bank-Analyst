import "@testing-library/jest-dom/vitest";

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../src/api", () => {
  const apiRequest = vi.fn();
  return {
    apiRequest,
    fetchCountryDetail: async (code) => {
      try {
        return await apiRequest(`/countries/${code}`);
      } catch (error) {
        if (error?.status === 404) return null;
        throw error;
      }
    },
  };
});

import { GlobalOverview } from "../src/pages/GlobalOverview";
import { apiRequest } from "../src/api";

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route element={<GlobalOverview />} path="/" />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("GlobalOverview", () => {
  it("lands in a neutral panel state and hydrates market detail only after focus", async () => {
    const originalIntersectionObserver = globalThis.IntersectionObserver;
    globalThis.IntersectionObserver = class {
      disconnect() {}
      observe() {}
      unobserve() {}
    };

    let resolveUnitedStatesBriefing;

    apiRequest.mockImplementation((path) => {
      if (path === "/pipeline/status") {
        return Promise.resolve({ status: "complete", steps: [] });
      }

      if (path === "/countries") {
        return Promise.resolve([
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
        ]);
      }

      if (path === "/indicators") {
        return Promise.resolve([
          {
            country_code: "BR",
            indicator_code: "NY.GDP.MKTP.KD.ZG",
            latest_value: 0.6,
            percent_change: -1.3,
            data_year: 2023,
            updated_at: "2026-04-11T10:00:00Z",
            is_anomaly: false,
          },
          {
            country_code: "US",
            indicator_code: "NY.GDP.MKTP.KD.ZG",
            latest_value: 3.1,
            percent_change: 0.8,
            data_year: 2024,
            updated_at: "2026-04-11T10:00:00Z",
            is_anomaly: false,
          },
        ]);
      }

      if (path === "/overview") {
        return Promise.resolve({
          summary:
            "Cross-market inflation pressure remains concentrated even as the monitored set no longer reads like a single-country story.",
          outlook: "cautious",
          risk_flags: [
            "Brazil and the United States are both carrying elevated inflation pressure in the current monitored set.",
            "Growth dispersion remains wide enough that the drilldown matters by market.",
          ],
          country_count: 2,
          country_codes: ["BR", "US"],
          source_date_range: "2010:2024",
        });
      }

      if (path === "/countries/BR") {
        return Promise.resolve({
          code: "BR",
          name: "Brazil",
          region: "Latin America & Caribbean",
          outlook: "cautious",
          macro_synthesis:
            "Growth remains weak while inflation pressure persists.",
          indicators: [
            {
              indicator_code: "NY.GDP.MKTP.KD.ZG",
              indicator_name: "GDP growth",
              latest_value: 0.6,
              percent_change: -1.3,
            },
            {
              indicator_code: "FP.CPI.TOTL.ZG",
              indicator_name: "Inflation",
              latest_value: 6.0,
              percent_change: 1.1,
            },
            {
              indicator_code: "SL.UEM.TOTL.ZS",
              indicator_name: "Unemployment",
              latest_value: 32.1,
              percent_change: -0.6,
            },
          ],
        });
      }

      if (path === "/countries/US") {
        return new Promise((resolve) => {
          resolveUnitedStatesBriefing = () =>
            resolve({
              code: "US",
              name: "United States",
              region: "North America",
              outlook: "bullish",
              macro_synthesis:
                "Growth is recovering with firmer domestic momentum.",
              indicators: [
                {
                  indicator_code: "NY.GDP.MKTP.KD.ZG",
                  indicator_name: "GDP growth",
                  latest_value: 3.1,
                  percent_change: 0.8,
                },
                {
                  indicator_code: "FP.CPI.TOTL.ZG",
                  indicator_name: "Inflation",
                  latest_value: 4.4,
                  percent_change: -0.9,
                },
                {
                  indicator_code: "SL.UEM.TOTL.ZS",
                  indicator_name: "Unemployment",
                  latest_value: 9.2,
                  percent_change: -0.4,
                },
              ],
            });
        });
      }

      return Promise.reject(new Error(`Unexpected path: ${path}`));
    });

    try {
      renderPage();

      expect(
        await screen.findByRole("heading", { name: "Global Overview" }),
      ).toBeInTheDocument();
      // Hero synthesis text is visible on arrival
      expect(
        screen.getByText(
          "Cross-market inflation pressure remains concentrated even as the monitored set no longer reads like a single-country story.",
        ),
      ).toBeInTheDocument();
      expect(
        screen.getAllByText(/Source window \/\/ 2010-2024/).length,
      ).toBeGreaterThan(0);
      // Risk flags from the overview response render in the risk strip
      expect(
        screen.getByText(/Brazil and the United States are both carrying/),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Growth dispersion remains wide/),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: "Open pipeline" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Review country queue" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Open market briefings" }),
      ).toBeInTheDocument();
      expect(screen.queryByText(/Focus market \/\//)).not.toBeInTheDocument();
      const statisticalAnomalyLabel = screen.getByText(
        "0 statistical anomalies",
      );
      expect(statisticalAnomalyLabel).toHaveClass("text-secondary");
      expect(statisticalAnomalyLabel).not.toHaveClass("text-critical");
      expect(screen.getByText("Primary stress point")).toBeInTheDocument();
      expect(screen.getByText("BR -1.30%")).toBeInTheDocument();
      expect(screen.getByText("No market focused")).toBeInTheDocument();
      expect(screen.getByText("Pressure watchlist")).toBeInTheDocument();
      expect(
        screen.getByRole("button", {
          name: "Focus Brazil market on world map",
        }),
      ).toBeInTheDocument();
      expect(screen.queryByText("Lead market")).not.toBeInTheDocument();
      // Note: Phase 2 may include background warming of country data
      // So we just check that the key initial calls happened
      const initialCalls = apiRequest.mock.calls.map(([path]) => path);
      expect(initialCalls).toContain("/overview");
      expect(initialCalls).toContain("/countries");

      const unitedStatesMarker = screen.getByRole("button", {
        name: "Focus United States market on world map",
      });

      fireEvent.click(unitedStatesMarker);

      expect(screen.getByText("Focused market")).toBeInTheDocument();
      expect(screen.getAllByText("United States").length).toBeGreaterThan(0);
      expect(unitedStatesMarker).toHaveAttribute("aria-expanded", "true");
      expect(unitedStatesMarker).toHaveAttribute(
        "aria-controls",
        "overview-map-popover",
      );
      expect(unitedStatesMarker).not.toHaveAttribute("aria-pressed");
      expect(
        screen.getByRole("region", { name: "United States market actions" }),
      ).toBeInTheDocument();
      const drilldownPanel = screen
        .getByRole("heading", { name: "Country drilldown" })
        .closest(".overview-panel");
      expect(drilldownPanel).not.toBeNull();
      expect(within(drilldownPanel).getByText("LOADING")).toBeInTheDocument();
      expect(apiRequest.mock.calls.map(([path]) => path)).toContain(
        "/countries/US",
      );

      resolveUnitedStatesBriefing();

      expect(
        await screen.findByText(
          "Growth is recovering with firmer domestic momentum.",
        ),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: "Open intelligence" }),
      ).toHaveAttribute("href", "/country/us");
      expect(screen.getByRole("link", { name: "Open market" })).toHaveAttribute(
        "href",
        "/country/us",
      );

      fireEvent.click(unitedStatesMarker);

      await waitFor(() => {
        expect(screen.getByText("No market focused")).toBeInTheDocument();
      });
      expect(unitedStatesMarker).toHaveAttribute("aria-expanded", "false");
    } finally {
      globalThis.IntersectionObserver = originalIntersectionObserver;
    }
  });
});
