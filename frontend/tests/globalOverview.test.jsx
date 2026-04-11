import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GlobalOverview } from "../src/pages/GlobalOverview";
import { apiRequest } from "../src/api";

vi.mock("../src/api", () => ({
  apiRequest: vi.fn(),
}));

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
  it("opens a map summary popover and keeps the stable market detail panel in sync", async () => {
    apiRequest.mockImplementation((path) => {
      if (path === "/pipeline/status") {
        return Promise.resolve({ status: "complete", steps: [] });
      }

      if (path === "/countries") {
        return Promise.resolve([
          {
            code: "ZA",
            name: "South Africa",
            region: "Sub-Saharan Africa",
          },
          {
            code: "NG",
            name: "Nigeria",
            region: "Sub-Saharan Africa",
          },
        ]);
      }

      if (path === "/indicators") {
        return Promise.resolve([
          {
            country_code: "ZA",
            indicator_code: "NY.GDP.MKTP.KD.ZG",
            latest_value: 0.6,
            percent_change: -1.3,
            updated_at: "2026-04-11T10:00:00Z",
            is_anomaly: false,
          },
          {
            country_code: "NG",
            indicator_code: "NY.GDP.MKTP.KD.ZG",
            latest_value: 3.1,
            percent_change: 0.8,
            updated_at: "2026-04-11T10:00:00Z",
            is_anomaly: false,
          },
        ]);
      }

      if (path === "/countries/ZA") {
        return Promise.resolve({
          code: "ZA",
          name: "South Africa",
          region: "Sub-Saharan Africa",
          outlook: "cautious",
          macro_synthesis: "Growth remains weak while inflation pressure persists.",
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

      if (path === "/countries/NG") {
        return Promise.resolve({
          code: "NG",
          name: "Nigeria",
          region: "Sub-Saharan Africa",
          outlook: "bullish",
          macro_synthesis: "Growth is recovering with firmer domestic momentum.",
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
      }

      return Promise.reject(new Error(`Unexpected path: ${path}`));
    });

    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Market detail" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open pipeline" })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Open pipeline" }),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Focus Nigeria market" }));

    expect(screen.getByText("Map focus")).toBeInTheDocument();
    expect(screen.getByText("Focused market")).toBeInTheDocument();
    expect(screen.getAllByText("Nigeria").length).toBeGreaterThan(0);
    expect(
      screen.getByRole("link", { name: "Open country intelligence" }),
    ).toHaveAttribute("href", "/country/ng");
    expect(screen.getByRole("link", { name: "Open market" })).toHaveAttribute(
      "href",
      "/country/ng",
    );

    fireEvent.click(screen.getByRole("button", { name: "Focus Nigeria market" }));

    expect(screen.queryByText("Map focus")).not.toBeInTheDocument();
  });
});