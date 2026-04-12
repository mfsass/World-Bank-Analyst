import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiRequest } from "../src/api";
import { PipelineTrigger } from "../src/pages/PipelineTrigger";

vi.mock("../src/api", () => ({
  apiRequest: vi.fn(),
}));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/trigger"]}>
      <Routes>
        <Route element={<PipelineTrigger />} path="/trigger" />
        <Route element={<div>Country page</div>} path="/country/:id" />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("PipelineTrigger", () => {
  it("keeps header actions as buttons and only enables the lead-market action after completion", async () => {
    apiRequest.mockImplementation((path, options = {}) => {
      if (path === "/pipeline/status") {
        return Promise.resolve({
          status: "idle",
          steps: [],
        });
      }

      if (path === "/pipeline/trigger") {
        expect(options).toMatchObject({ method: "POST" });

        return Promise.resolve({
          status: "complete",
          started_at: "2026-04-12T10:00:00Z",
          completed_at: "2026-04-12T10:00:03Z",
          steps: [
            { name: "fetch", status: "complete", duration_ms: 400 },
            { name: "analyse", status: "complete", duration_ms: 600 },
            { name: "synthesise", status: "complete", duration_ms: 1200 },
            { name: "store", status: "complete", duration_ms: 300 },
          ],
        });
      }

      return Promise.reject(new Error(`Unexpected path: ${path}`));
    });

    renderPage();

    const runButton = await screen.findByRole("button", { name: "Run pipeline" });
    const openLeadMarketButton = screen.getByRole("button", {
      name: "Open lead market",
    });

    expect(screen.queryByRole("link", { name: "Run pipeline" })).not.toBeInTheDocument();
    expect(openLeadMarketButton).toBeDisabled();

    fireEvent.click(runButton);

    await waitFor(() => {
      expect(openLeadMarketButton).toBeEnabled();
    });

    fireEvent.click(openLeadMarketButton);

    expect(screen.getByText("Country page")).toBeInTheDocument();
  });

  it("renders the failed execution state and keeps the lead-market action blocked", async () => {
    apiRequest.mockResolvedValue({
      status: "failed",
      started_at: "2026-04-12T10:00:00Z",
      completed_at: "2026-04-12T10:00:03Z",
      error: "Live AI degraded coverage for one indicator.",
      steps: [
        { name: "fetch", status: "complete", duration_ms: 400 },
        { name: "analyse", status: "complete", duration_ms: 600 },
        { name: "synthesise", status: "failed", duration_ms: 1200 },
        { name: "store", status: "pending" },
      ],
    });

    renderPage();

    expect(
      await screen.findByText(
        "The run stopped while generating the analyst narratives. Latest duration: 1200ms.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Open lead market",
      }),
    ).toBeDisabled();
  });
});
