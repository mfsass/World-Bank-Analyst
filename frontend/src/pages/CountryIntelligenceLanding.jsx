import { Link } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { StatusPill } from "../components/StatusPill";

export function CountryIntelligenceLanding() {
  return (
    <div className="page page--country-landing container">
      <PageHeader
        actions={
          <div className="button-row">
            <Link className="btn-primary" to="/">
              Open global overview
            </Link>
            <Link className="btn-ghost" to="/trigger">
              Open pipeline trigger
            </Link>
          </div>
        }
        description="Country intelligence is intentionally market-specific. Use the panel-first overview to choose a market once you want a single-country briefing."
        eyebrow="COUNTRY INTELLIGENCE"
        meta="Market-specific briefings // neutral entry // no default market bias"
        title="Choose a market when you want a drilldown"
      />

      <section className="detail-grid section-gap">
        <article className="card">
          <div className="panel-header">
            <div>
              <p className="text-label">Panel-first entry</p>
              <h2 className="text-headline mt-3">
                Start from the monitored panel
              </h2>
            </div>
            <StatusPill tone="neutral">Current</StatusPill>
          </div>
          <p className="text-body text-secondary mt-4">
            The global overview no longer lands on a preselected market. Open
            the world map or the drilldown queue to choose the country you want
            to inspect.
          </p>
          <div className="button-row mt-4">
            <Link className="btn-primary" to="/">
              Open global overview
            </Link>
          </div>
        </article>

        <article className="card">
          <div className="panel-header">
            <div>
              <p className="text-label">Direct route</p>
              <h2 className="text-headline mt-3">
                Use a market code when you already know the target
              </h2>
            </div>
            <StatusPill tone="neutral">Optional</StatusPill>
          </div>
          <p className="text-body text-secondary mt-4">
            Direct country routes stay available for deep links. Open paths like
            <span className="text-primary"> /country/us </span>
            or
            <span className="text-primary"> /country/br </span>
            once the current slice has materialised the briefing you want.
          </p>
        </article>
      </section>
    </div>
  );
}

export default CountryIntelligenceLanding;
