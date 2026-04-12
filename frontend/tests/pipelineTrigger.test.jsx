import "@testing-library/jest-dom/vitest";

import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
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
        <Route element={<div>Country landing</div>} path="/country" />
        <Route element={<div>Country page</div>} path="/country/:id" />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.useRealTimers();
  delete window.matchMedia;
});

describe("PipelineTrigger", () => {
  it("keeps real run actions as buttons and only enables country intelligence after a completed live run", async () => {
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

    const runButton = await screen.findByRole("button", {
      name: "Run pipeline",
    });
    const openCountryPageButton = screen.getByRole("button", {
      name: "Open country intelligence",
    });

    expect(
      screen.queryByRole("link", { name: "Run pipeline" }),
    ).not.toBeInTheDocument();
    expect(openCountryPageButton).toBeDisabled();

    fireEvent.click(runButton);

    await waitFor(() => {
      expect(openCountryPageButton).toBeEnabled();
    });

    fireEvent.click(openCountryPageButton);

    expect(screen.getByText("Country landing")).toBeInTheDocument();
  });

  it("opens the demo walkthrough as a browser-only modal and lets the user step through it", async () => {
    apiRequest.mockResolvedValue({
      status: "idle",
      steps: [],
    });

    renderPage();

    await waitFor(() => {
      expect(apiRequest).toHaveBeenCalledTimes(1);
    });

    vi.clearAllMocks();
    vi.useFakeTimers();

    fireEvent.click(screen.getByRole("radio", { name: "Demo walkthrough" }));

    const replayTrigger = screen.getByRole("button", {
      name: "Replay walkthrough",
    });

    fireEvent.click(replayTrigger);

    const dialog = screen.getByRole("dialog", {
      name: "Replay walkthrough",
    });
    const dialogQueries = within(dialog);

    expect(
      screen.getByText(
        /animates through the shared pipeline stage model in the browser/i,
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText("SIMULATED").length).toBeGreaterThan(0);
    expect(dialogQueries.getByText("AUTO-PLAY")).toBeInTheDocument();
    expect(dialogQueries.getByText("Replay activity")).toBeInTheDocument();
    expect(
      dialogQueries.getByRole("heading", { name: "Fetch and normalize" }),
    ).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(2600);
    });

    expect(
      dialogQueries.getByRole("heading", { name: "Statistical signal layer" }),
    ).toBeInTheDocument();

    fireEvent.click(
      dialogQueries.getByRole("button", { name: "Pause auto-play" }),
    );
    fireEvent.click(dialogQueries.getByRole("button", { name: "Next stage" }));

    expect(
      dialogQueries.getByRole("heading", { name: "Country + panel synthesis" }),
    ).toBeInTheDocument();

    const persistOutputsCard = dialogQueries
      .getAllByText("Persist outputs")[0]
      .closest("button");
    expect(persistOutputsCard).not.toBeNull();

    fireEvent.click(persistOutputsCard);

    expect(
      dialogQueries.getByRole("heading", { name: "Persist outputs" }),
    ).toBeInTheDocument();
    expect(dialogQueries.getByText("MANUAL")).toBeInTheDocument();
    expect(apiRequest).not.toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: "Open country intelligence" }),
    ).toBeDisabled();
  });

  it("moves keyboard focus with radio selection changes", async () => {
    apiRequest.mockResolvedValue({
      status: "idle",
      steps: [],
    });

    renderPage();

    const realRunRadio = await screen.findByRole("radio", { name: "Real run" });
    realRunRadio.focus();

    fireEvent.keyDown(realRunRadio, { key: "ArrowRight" });

    const demoRadio = screen.getByRole("radio", { name: "Demo walkthrough" });
    expect(demoRadio).toHaveFocus();
    expect(demoRadio).toHaveAttribute("aria-checked", "true");
    expect(realRunRadio).toHaveAttribute("aria-checked", "false");
  });

  it("defaults the replay modal to manual mode for reduced-motion users", async () => {
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: query === "(prefers-reduced-motion: reduce)",
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    apiRequest.mockResolvedValue({
      status: "idle",
      steps: [],
    });

    renderPage();

    await waitFor(() => {
      expect(apiRequest).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByRole("radio", { name: "Demo walkthrough" }));
    fireEvent.click(screen.getByRole("button", { name: "Replay walkthrough" }));

    const dialog = await screen.findByRole("dialog", {
      name: "Replay walkthrough",
    });

    expect(within(dialog).getByText("MANUAL")).toBeInTheDocument();
  });

  it("closes the walkthrough on escape and returns focus to the replay trigger", async () => {
    apiRequest.mockResolvedValue({
      status: "idle",
      steps: [],
    });

    renderPage();

    await waitFor(() => {
      expect(apiRequest).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByRole("radio", { name: "Demo walkthrough" }));

    const replayTrigger = screen.getByRole("button", {
      name: "Replay walkthrough",
    });

    replayTrigger.focus();
    fireEvent.click(replayTrigger);

    expect(
      await screen.findByRole("dialog", { name: "Replay walkthrough" }),
    ).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });

    await waitFor(() => {
      expect(
        screen.queryByRole("dialog", { name: "Replay walkthrough" }),
      ).not.toBeInTheDocument();
    });

    expect(replayTrigger).toHaveFocus();
  });

  it("renders live stage narration while synthesis is running", async () => {
    apiRequest.mockResolvedValue({
      status: "running",
      started_at: "2026-04-12T10:00:00Z",
      steps: [
        { name: "fetch", status: "complete", duration_ms: 400 },
        { name: "analyse", status: "complete", duration_ms: 600 },
        { name: "synthesise", status: "running" },
        { name: "store", status: "pending" },
      ],
    });

    renderPage();

    expect(await screen.findByText("Live operation")).toBeInTheDocument();
    expect(
      screen.getByText(
        "> Gathering structured indicator evidence for the model.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /This is the longest stage because the model works through the full 17-country panel\./,
      ),
    ).toBeInTheDocument();
  });

  it("renders the failed execution state and keeps the country intelligence action blocked", async () => {
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
        name: "Open country intelligence",
      }),
    ).toBeDisabled();
  });
});
