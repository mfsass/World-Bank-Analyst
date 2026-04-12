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
import { afterEach, describe, expect, it } from "vitest";

import { AppShell } from "../src/components/AppShell";

function renderShell(initialEntries = ["/"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route element={<AppShell />}>
          <Route element={<div>Overview page</div>} path="/" />
          <Route element={<div>Country page</div>} path="/country/:id" />
          <Route element={<div>Pipeline page</div>} path="/pipeline" />
          <Route element={<div>Trigger page</div>} path="/trigger" />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
});

describe("AppShell", () => {
  it("keeps country intelligence active for any country route", () => {
    renderShell(["/country/ng"]);

    const primaryNav = screen.getByRole("navigation", { name: "Primary" });
    const countryLink = within(primaryNav).getByRole("link", {
      name: "Country Intelligence",
    });

    expect(countryLink).toHaveClass("shell-nav__link--active");
  });

  it("uses product chrome instead of implementation scaffolding labels", () => {
    renderShell(["/"]);
    const expectedBuildModeCopy = import.meta.env.DEV
      ? "Development"
      : "Production";

    expect(screen.queryByText("Shared Shell")).not.toBeInTheDocument();
    expect(screen.queryByText("Representative Chrome")).not.toBeInTheDocument();
    expect(screen.getByText("Build")).toBeInTheDocument();
    expect(screen.getByText(expectedBuildModeCopy)).toBeInTheDocument();
    expect(screen.getAllByRole("navigation")).toHaveLength(1);
    expect(
      screen.queryByRole("button", { name: "Notifications" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Analyst profile" }),
    ).not.toBeInTheDocument();
  });

  it("closes the primary nav after a route change", async () => {
    renderShell(["/"]);

    const menuButton = screen.getByRole("button", { name: "Menu" });
    const primaryNav = screen.getByRole("navigation", { name: "Primary" });

    fireEvent.click(menuButton);
    expect(primaryNav).toHaveClass("shell-nav--open");
    expect(menuButton).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(
      within(primaryNav).getByRole("link", { name: "How It Works" }),
    );

    await waitFor(() => {
      expect(menuButton).toHaveAttribute("aria-expanded", "false");
    });

    expect(primaryNav).not.toHaveClass("shell-nav--open");
    expect(screen.getByText("Pipeline page")).toBeInTheDocument();
  });
});
