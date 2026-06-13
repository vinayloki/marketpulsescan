import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search } from 'lucide-react';

function Scanner() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In production, this would fetch from our actual FastAPI backend
    // For now, we mock the data since the backend might not be running yet.
    axios.get('http://localhost:8000/api/scanner/stage2')
      .then(response => {
        setData(response.data.data);
        setLoading(false);
      })
      .catch(error => {
        console.error("Error fetching scanner data", error);
        // Fallback mock data
        setData([
          { symbol: "TATASTEEL", name: "Tata Steel", sector: "Metals", score: 92, rs_rating: 88, price: 154.2, sma_50: 140, sma_200: 125 },
          { symbol: "RELIANCE", name: "Reliance Ind", sector: "Energy", score: 85, rs_rating: 81, price: 2950, sma_50: 2800, sma_200: 2650 },
          { symbol: "ZOMATO", name: "Zomato Ltd", sector: "Consumer Services", score: 95, rs_rating: 94, price: 165, sma_50: 145, sma_200: 110 }
        ]);
        setLoading(false);
      });
  }, []);

  return (
    <div>
      <div className="flex justify-between items-center" style={{ marginBottom: '2rem' }}>
        <h2>Stage 2 Scanner</h2>
        <div style={{ position: 'relative', width: '300px' }}>
          <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input 
            type="text" 
            placeholder="Search symbols..." 
            style={{ 
              width: '100%', 
              padding: '0.75rem 1rem 0.75rem 2.5rem', 
              borderRadius: 'var(--radius-md)', 
              border: '1px solid var(--border-color)', 
              background: 'var(--bg-card)',
              color: 'white',
              outline: 'none'
            }} 
          />
        </div>
      </div>
      
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Sector</th>
              <th>Stage Score</th>
              <th>RS Rating</th>
              <th>Price</th>
              <th>50 SMA</th>
              <th>200 SMA</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan="7" style={{ textAlign: 'center', padding: '2rem' }}>Loading...</td></tr>
            ) : data.map((stock, idx) => (
              <tr key={idx}>
                <td style={{ fontWeight: 600, color: 'var(--accent-blue)' }}>{stock.symbol}</td>
                <td>{stock.sector}</td>
                <td>
                  <span className={`badge ${stock.score > 90 ? 'green' : 'blue'}`}>
                    {stock.score}
                  </span>
                </td>
                <td>{stock.rs_rating}</td>
                <td>₹{stock.price}</td>
                <td>{stock.sma_50}</td>
                <td>{stock.sma_200}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Scanner;
