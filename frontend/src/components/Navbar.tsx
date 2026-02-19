import { Link, useLocation } from 'react-router-dom';
import './Navbar.css';

function Navbar() {
  const location = useLocation();

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <h1>🦁 Wildlife MLOps</h1>
      </div>
      <div className="navbar-links">
        <Link to="/" className={location.pathname === '/' ? 'active' : ''}>
          Dashboard
        </Link>
        <Link to="/predict" className={location.pathname === '/predict' ? 'active' : ''}>
          Predict
        </Link>
        <Link to="/predictions" className={location.pathname === '/predictions' ? 'active' : ''}>
          Predictions
        </Link>
        <Link to="/species" className={location.pathname === '/species' ? 'active' : ''}>
          Species
        </Link>
        <Link to="/system" className={location.pathname === '/system' ? 'active' : ''}>
          System
        </Link>
      </div>
    </nav>
  );
}

export default Navbar;
