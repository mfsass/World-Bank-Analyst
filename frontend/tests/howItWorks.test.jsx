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
  it("keeps the approved 17-country scope and current runtime labels free of stale copy", () => {
    renderPage();

    expect(
      screen.getByRole("heading", { name: "How It Works" }),
    ).toBeInTheDocument();
    expect(screen.getByText("17 x 6")).toBeInTheDocument();
    expect(screen.getByText("LOCAL-FIRST")).toBeInTheDocument();
    expect(screen.getByText("LIVE 2-STEP")).toBeInTheDocument();
    expect(screen.getByText("LOCAL // FIRESTORE")).toBeInTheDocument();
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
