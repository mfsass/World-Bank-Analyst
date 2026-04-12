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
  it("shows the approved 17-country scope and avoids stale 15-country copy", () => {
    renderPage();

    expect(
      screen.getByRole("heading", { name: "How It Works" }),
    ).toBeInTheDocument();
    expect(screen.getByText("17 x 6")).toBeInTheDocument();
    expect(screen.queryByText("15 x 6")).not.toBeInTheDocument();
    expect(
      screen.queryByText(/Fifteen countries and six approved indicators/i),
    ).not.toBeInTheDocument();
  });
});
