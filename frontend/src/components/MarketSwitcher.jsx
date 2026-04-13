import PropTypes from "prop-types";

import { Link } from "react-router-dom";

export function MarketSwitcher({ label, items, activeCode, getHref }) {
  return (
    <section className="market-switcher">
      {label ? <p className="text-label">{label}</p> : null}
      <div className={`market-switcher__row${label ? " mt-3" : ""}`}>
        {items.map((item) => {
          const isActive = item.code === activeCode;
          const className = `market-switcher__pill${isActive ? " market-switcher__pill--active" : ""}`;

          if (!getHref) {
            return (
              <span className={className} key={item.code}>
                {item.code}
              </span>
            );
          }

          return (
            <Link className={className} key={item.code} to={getHref(item)}>
              {item.code}
            </Link>
          );
        })}
      </div>
    </section>
  );
}

MarketSwitcher.propTypes = {
  label: PropTypes.string,
  items: PropTypes.arrayOf(
    PropTypes.shape({
      code: PropTypes.string.isRequired,
    }),
  ).isRequired,
  activeCode: PropTypes.string.isRequired,
  getHref: PropTypes.func,
};
