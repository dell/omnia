import { Link } from 'react-router-dom';

export const NotFound = () => {
  return (
    <div className="card notfound-card">
      <h2 className="notfound-title">Page Not Found</h2>
      <p className="notfound-text">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link to="/" className="button button-primary">
        Go to Overview
      </Link>
    </div>
  );
};
