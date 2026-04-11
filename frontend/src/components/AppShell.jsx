import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

const PRIMARY_NAV_ITEMS = [
  { to: "/", label: "Global Overview", exact: true },
  { to: "/country/br", label: "Country Intelligence" },
  { to: "/pipeline", label: "How It Works" },
  { to: "/trigger", label: "Pipeline Trigger" },
];

function isItemActive(pathname, item) {
  if (item.to === "/") {
    return pathname === "/";
  }

  if (item.to === "/country/br") {
    return pathname.startsWith("/country/");
  }

  return pathname.startsWith(item.to);
}

function getNavLinkClass(isActive) {
  return `shell-nav__link${isActive ? " shell-nav__link--active" : ""}`;
}

export function AppShell() {
  const location = useLocation();
  const [isNavOpen, setIsNavOpen] = useState(false);

  useEffect(() => {
    setIsNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="app-shell">
      <header className="shell-topbar">
        <div className="shell-topbar__brand">
          <Link className="shell-brand" to="/">
            <span className="material-symbols-outlined shell-brand__icon">
              auto_awesome
            </span>
            <span className="shell-brand__name">WORLD BANK ANALYST</span>
          </Link>

          <button
            aria-controls="shell-primary-nav"
            aria-expanded={isNavOpen}
            className="shell-nav-toggle"
            onClick={() => setIsNavOpen((currentValue) => !currentValue)}
            type="button"
          >
            Menu
          </button>
        </div>

        <nav
          aria-label="Primary"
          className={`shell-nav${isNavOpen ? " shell-nav--open" : ""}`}
          id="shell-primary-nav"
        >
          {PRIMARY_NAV_ITEMS.map((item) => {
            const isActive = isItemActive(location.pathname, item);

            return (
              <NavLink
                aria-current={isActive ? "page" : undefined}
                className={() => getNavLinkClass(isActive)}
                end={item.exact}
                key={item.to}
                to={item.to}
              >
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="shell-topbar__status" aria-label="Current slice status">
          <span className="status-dot" />
          <div>
            <p className="text-label">Current slice</p>
            <span className="shell-topbar__status-copy">Live-compatible</span>
          </div>
        </div>
      </header>

      <div className="shell-body">
        <div className="shell-content">
          <main className="shell-main">
            <Outlet />
          </main>

          <footer className="shell-footer">
            <div className="shell-footer__brand">WORLD BANK ANALYST</div>
            <p className="shell-footer__disclaimer">
              AI-generated content may contain inaccuracies. Verify before acting.
            </p>
          </footer>
        </div>
      </div>
    </div>
  );
}
