import PropTypes from "prop-types";

import { StatusPill } from "./StatusPill";

export function AIInsightPanel({
  eyebrow,
  title,
  tone,
  status,
  children,
  footer,
}) {
  return (
    <section className="ai-insight ai-insight-panel">
      <div className="ai-insight-panel__header">
        <div>
          {eyebrow ? <p className="text-label">{eyebrow}</p> : null}
          <h2 className="text-headline mt-3">
            <span
              aria-hidden="true"
              className="ai-insight__icon material-symbols-outlined"
            >
              auto_awesome
            </span>
            {title}
          </h2>
        </div>
        {status ? <StatusPill tone={tone}>{status}</StatusPill> : null}
      </div>
      <div className="ai-insight-panel__body mt-4">{children}</div>
      {footer ? (
        <div className="ai-insight-panel__footer mt-4">{footer}</div>
      ) : null}
    </section>
  );
}

AIInsightPanel.propTypes = {
  eyebrow: PropTypes.string,
  title: PropTypes.string.isRequired,
  tone: PropTypes.string,
  status: PropTypes.string,
  children: PropTypes.node.isRequired,
  footer: PropTypes.node,
};
