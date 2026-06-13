import React from 'react';
import { TrendingUp, TrendingDown, Activity, Zap } from 'lucide-react';

function Dashboard() {
  return (
    <div>
      <h2 style={{ marginBottom: '2rem' }}>Market Overview</h2>
      
      <div className="grid grid-cols-3">
        <div className="card">
          <div className="flex justify-between items-center" style={{ marginBottom: '1rem' }}>
            <h3 style={{ color: 'var(--text-muted)' }}>Market Regime</h3>
            <Activity color="var(--accent-blue)" />
          </div>
          <h2>Bull Market</h2>
          <p>Nifty 50 is trading above its 200-day EMA.</p>
        </div>
        
        <div className="card">
          <div className="flex justify-between items-center" style={{ marginBottom: '1rem' }}>
            <h3 style={{ color: 'var(--text-muted)' }}>Stage 2 Breakouts</h3>
            <Zap color="var(--accent-purple)" />
          </div>
          <h2>42 Stocks</h2>
          <p>New setups found in the latest scan.</p>
        </div>

        <div className="card">
          <div className="flex justify-between items-center" style={{ marginBottom: '1rem' }}>
            <h3 style={{ color: 'var(--text-muted)' }}>Top Sector</h3>
            <TrendingUp color="var(--accent-green)" />
          </div>
          <h2>Auto & Components</h2>
          <p>Highest Relative Strength across the board.</p>
        </div>
      </div>
      
      <h2 style={{ marginTop: '3rem', marginBottom: '1.5rem' }}>Sector Rotation Heatmap</h2>
      <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        Sector rotation visualization will be displayed here.
      </div>
    </div>
  );
}

export default Dashboard;
