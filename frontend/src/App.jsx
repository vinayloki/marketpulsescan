import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Activity, LayoutDashboard, List, Bell } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Scanner from './pages/Scanner';

function App() {
  return (
    <Router>
      <div className="nav-header flex justify-between items-center">
        <h1 className="brand flex items-center gap-4">
          <Activity size={24} color="var(--accent-blue)" />
          MarketPulse
        </h1>
        <nav className="flex gap-4">
          <Link to="/" className="nav-link flex items-center gap-4"><LayoutDashboard size={18} /> Dashboard</Link>
          <Link to="/scanner" className="nav-link flex items-center gap-4"><Activity size={18} /> Scanner</Link>
          <Link to="/watchlists" className="nav-link flex items-center gap-4"><List size={18} /> Watchlists</Link>
          <Link to="/alerts" className="nav-link flex items-center gap-4"><Bell size={18} /> Alerts</Link>
        </nav>
      </div>

      <div className="container">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scanner" element={<Scanner />} />
          <Route path="/watchlists" element={<div className="card">Watchlists coming soon</div>} />
          <Route path="/alerts" element={<div className="card">Alerts coming soon</div>} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
