import { useEffect, useState } from 'react';
import './Dashboard.css';

interface Stats {
  totalPredictions: number;
  totalSpecies: number;
  avgConfidence: number;
}

function Dashboard() {
  const [stats, setStats] = useState<Stats>({
    totalPredictions: 0,
    totalSpecies: 0,
    avgConfidence: 0
  });

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const [speciesRes, predictionsRes, statsRes] = await Promise.all([
        fetch('http://localhost:8080/api/species/count'),
        fetch('http://localhost:8080/api/predictions'),
        fetch('http://localhost:8080/api/predictions/stats')
      ]);

      const speciesCount = await speciesRes.json();
      const predictions = await predictionsRes.json();
      const predStats = await statsRes.json();

      setStats({
        totalSpecies: speciesCount,
        totalPredictions: predictions.length,
        avgConfidence: predStats.averageConfidence || 0
      });
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  return (
    <div className="dashboard">
      <h1>Dashboard</h1>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Predictions</h3>
          <p className="stat-value">{stats.totalPredictions}</p>
        </div>

        <div className="stat-card">
          <h3>Species Tracked</h3>
          <p className="stat-value">{stats.totalSpecies}</p>
        </div>

        <div className="stat-card">
          <h3>Avg Confidence</h3>
          <p className="stat-value">{(stats.avgConfidence * 100).toFixed(1)}%</p>
        </div>
      </div>

      <div className="info-section">
        <h2>Welcome to Wildlife MLOps Platform</h2>
        <p>Use the navigation above to:</p>
        <ul>
          <li><strong>Predict:</strong> Upload wildlife images for classification</li>
          <li><strong>Predictions:</strong> View all prediction history</li>
          <li><strong>Species:</strong> Manage species database</li>
          <li><strong>System:</strong> Monitor system health</li>
        </ul>
      </div>
    </div>
  );
}

export default Dashboard;
