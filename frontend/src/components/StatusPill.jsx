import PropTypes from "prop-types";

export function StatusPill({ children, tone = "neutral" }) {
  return <span className={`status-pill status-pill--${tone}`}>{children}</span>;
}

StatusPill.propTypes = {
  children: PropTypes.node.isRequired,
  tone: PropTypes.string,
};
