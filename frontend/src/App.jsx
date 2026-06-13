import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { Activity } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Scanner from './pages/Scanner';

function App() {
  return (
    <Router>
      <header className="nav-header">
        <h1 className="brand">
          <Activity size={20} />
          MarketPulse
        </h1>
        <nav>
          <NavLink to="/"        end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>Dashboard</NavLink>
          <NavLink to="/scanner"     className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>Scanner</NavLink>
          <NavLink to="/watchlists"  className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>Watchlists</NavLink>
          <NavLink to="/alerts"      className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>Alerts</NavLink>
        </nav>
      </header>

      <main className="container">
        <Routes>
          <Route path="/"           element={<Dashboard />} />
          <Route path="/scanner"    element={<Scanner />} />
          <Route path="/watchlists" element={<ComingSoon title="Watchlists" icon="📋" />} />
          <Route path="/alerts"     element={<ComingSoon title="Alerts"     icon="🔔" />} />
        </Routes>
      </main>
    </Router>
  );
}

function ComingSoon({ title, icon }) {
  return (
    <div className="card" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
      <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>{icon}</div>
      <h2>{title}</h2>
      <p style={{ marginTop: '0.5rem' }}>{title} functionality is coming soon.</p>
    </div>
  );
}

export default App;
