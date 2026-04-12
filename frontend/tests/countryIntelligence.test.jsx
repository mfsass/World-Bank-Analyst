import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CountryIntelligence } from "../src/pages/CountryIntelligence";
import { apiRequest } from "../src/api";

vi.mock("../src/api", () => ({
  apiRequest: vi.fn(),
}));

function renderPage(initialEntry = "/country/br") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route element={<CountryIntelligence />} path="/country/:id" />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("CountryIntelligence", () => {
  it("keeps breadcrumb and header shell visible while loading", () => {
    apiRequest.mockImplementation(() => new Promise(() => {}));

    const { container } = renderPage();

    expect(screen.getByText("Global Overview")).toBeInTheDocument();
    expect(screen.getByText("Switch market")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "BR" })).toBeInTheDocument();
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
          macro_synthesis:
            "Inflation remains elevated while growth is subdued.",
          risk_flags: ["Inflation pressure persists"],
          indicators: [
            {
              indicator_code: "NY.GDP.MKTP.KD.ZG",
              indicator_name: "GDP growth",
              latest_value: 0.6,
              percent_change: -1.3,
              data_year: 2023,
              ai_analysis: "Growth remains subdued.",
              is_anomaly: false,
            },
            {
              indicator_code: "FP.CPI.TOTL.ZG",
              indicator_name: "Inflation",
              latest_value: 6,
              percent_change: 1.1,
              data_year: 2023,
              ai_analysis: "Inflation remains above comfort range.",
              is_anomaly: true,
            },
            {
              indicator_code: "SL.UEM.TOTL.ZS",
              indicator_name: "Unemployment",
              latest_value: 32.1,
              percent_change: -0.6,
              data_year: 2023,
              ai_analysis: "Labor-market stress remains high.",
              is_anomaly: false,
            },
            {
              indicator_code: "GC.DOD.TOTL.GD.ZS",
              indicator_name: "Government debt",
              latest_value: 74.8,
              percent_change: 3.7,
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

    const briefingHeading = screen.getByRole("heading", {
      name: "Country briefing",
    });
    const postureLabel = screen.getByText("Current posture");

    expect(
      screen.getByText("Inflation remains elevated while growth is subdued."),
    ).toBeInTheDocument();
    expect(screen.getByText("Source window // 2017-2023")).toBeInTheDocument();
    expect(screen.getByText("Latest data year // 2023")).toBeInTheDocument();
    expect(
      briefingHeading.compareDocumentPosition(postureLabel) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.getByRole("link", { name: "US" })).toBeInTheDocument();
  });
});
