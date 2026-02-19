import { useEffect, useState } from 'react';
import './System.css';

function System() {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/health');
      const data = await response.json();
      setHealth({ status: 'UP', ...data });
    } catch (error) {
      setHealth({ status: 'DOWN', message: 'Backend not reachable' });
    }
  };

  return (
    <div className="system">
      <h1>System Status</h1>

      <div className="status-grid">
        <div className={`status-card ${health?.status === 'UP' ? 'up' : 'down'}`}>
          <h3>Backend API</h3>
          <p className="status">{health?.status || 'CHECKING...'}</p>
          <p className="url">http://localhost:8080</p>
        </div>

        <div className="status-card unknown">
          <h3>ML Service</h3>
          <p className="status">NOT IMPLEMENTED</p>
          <p className="url">http://localhost:8000</p>
        </div>

        <div className="status-card up">
          <h3>Database</h3>
          <p className="status">UP (H2 Dev Mode)</p>
          <p className="url">In-Memory</p>
        </div>

        <div className="status-card unknown">
          <h3>Kafka</h3>
          <p className="status">NOT CONFIGURED</p>
          <p className="url">localhost:9092</p>
        </div>

        <div className="status-card unknown">
          <h3>Redis</h3>
          <p className="status">NOT CONFIGURED</p>
          <p className="url">localhost:6379</p>
        </div>
      </div>
    </div>
  );
}

export default System;
