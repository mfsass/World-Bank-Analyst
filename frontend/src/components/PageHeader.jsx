import PropTypes from "prop-types";

export function PageHeader({ eyebrow, title, description, meta, actions }) {
  return (
    <header className="page-header">
      <div className="page-header__body">
        {eyebrow ? <p className="text-label">{eyebrow}</p> : null}
        <h1 className="text-display page-header__title">{title}</h1>
        {meta ? (
          <p className="page-header__meta text-label mt-3">{meta}</p>
        ) : null}
        {description ? (
          <p className="text-body text-secondary mt-4 page-header__description">
            {description}
          </p>
        ) : null}
      </div>

      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  );
}

PageHeader.propTypes = {
  eyebrow: PropTypes.string,
  title: PropTypes.oneOfType([PropTypes.string, PropTypes.node]).isRequired,
  description: PropTypes.string,
  meta: PropTypes.string,
  actions: PropTypes.node,
};
