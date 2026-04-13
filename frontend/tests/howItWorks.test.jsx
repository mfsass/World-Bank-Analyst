import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { HowItWorks } from "../src/pages/HowItWorks";

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/pipeline"]}>
      <Routes>
        <Route element={<HowItWorks />} path="/pipeline" />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
});

describe("HowItWorks", () => {
  it("keeps the approved scope while explaining the shared stage model and the real-vs-demo trigger split", () => {
    renderPage();

    expect(
      screen.getByRole("heading", { name: "How It Works" }),
    ).toBeInTheDocument();
    expect(screen.getByText("17 x 6")).toBeInTheDocument();
    expect(screen.getByText("LOCAL-FIRST")).toBeInTheDocument();
    expect(screen.getByText("2-STEP + PANEL")).toBeInTheDocument();
    expect(screen.getByText("LOCAL // FIRESTORE")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Real run" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Demo walkthrough" }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("heading", { name: "Country + overview synthesis" }).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("heading", { name: "Persist outputs" }).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getByText(/frontend-only simulation/i),
    ).toBeInTheDocument();
    expect(screen.queryByText("15 x 6")).not.toBeInTheDocument();
    expect(screen.queryByText("LOCAL DEFAULTS")).not.toBeInTheDocument();
    expect(
      screen.queryByText(/provider wiring remains a later phase/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Current + target")).not.toBeInTheDocument();
    expect(
      screen.queryByText(/Fifteen countries and six approved indicators/i),
    ).not.toBeInTheDocument();
  });
});
