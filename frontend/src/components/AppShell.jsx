import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

const PRIMARY_NAV_ITEMS = [
  { to: "/", label: "Global Overview", exact: true },
  { to: "/country", label: "Country Intelligence" },
  { to: "/pipeline", label: "How It Works" },
  { to: "/trigger", label: "Pipeline Trigger" },
];

function isItemActive(pathname, item) {
  if (item.to === "/") {
    return pathname === "/";
  }

  if (item.to === "/country") {
    return pathname === "/country" || pathname.startsWith("/country/");
  }

  return pathname.startsWith(item.to);
}

function getNavLinkClass(isActive) {
  return `shell-nav__link${isActive ? " shell-nav__link--active" : ""}`;
}

export function AppShell() {
  const location = useLocation();
  const [isNavOpen, setIsNavOpen] = useState(false);
  const buildModeLabel = import.meta.env.DEV ? "Development" : "Production";

  useEffect(() => {
    setIsNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="app-shell">
      <header className="shell-topbar">
        <div className="shell-topbar__brand">
          <Link className="shell-brand" to="/">
            <span className="material-symbols-outlined shell-brand__icon ui-inline-icon">
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

        <div className="shell-topbar__status" aria-label="Current build mode">
          <span className="status-dot status-dot--steady status-dot--idle" />
          <div>
            <p className="text-label">Build</p>
            <span className="shell-topbar__status-copy">{buildModeLabel}</span>
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
            <div className="shell-footer__rule" aria-hidden="true" />
            <p className="shell-footer__disclaimer">
              AI-generated content may contain inaccuracies. Verify before acting.
            </p>
            <div className="shell-footer__rule" aria-hidden="true" />
            <a
              className="shell-footer__credit"
              href="https://linkedin.com/in/sass-markus"
              rel="noopener noreferrer"
              target="_blank"
            >
              <svg
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
                className="shell-footer__credit-icon"
              >
                <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
              </svg>
              Markus Sass
            </a>
          </footer>
        </div>
      </div>
    </div>
  );
}
