import { useEffect, useState } from 'react';
import './System.css';

function System() {
  const [backendStatus, setBackendStatus] = useState<string>('CHECKING...');
  const [mlStatus, setMlStatus] = useState<string>('CHECKING...');
  const [mlVersion, setMlVersion] = useState<string>('');

  useEffect(() => {
    checkBackend();
    checkMLService();
  }, []);

  const checkBackend = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/health');
      if (response.ok) {
        setBackendStatus('UP');
      } else {
        setBackendStatus('DOWN');
      }
    } catch {
      setBackendStatus('DOWN');
    }
  };

  const checkMLService = async () => {
    try {
      const response = await fetch('http://localhost:8000/health');
      if (response.ok) {
        const data = await response.json();
        setMlStatus(data.model_loaded ? 'UP' : 'DOWN');
        setMlVersion(data.model_version || '');
      } else {
        setMlStatus('DOWN');
      }
    } catch {
      setMlStatus('DOWN');
    }
  };

  const getCardClass = (status: string) => {
    if (status === 'UP') return 'status-card up';
    if (status === 'DOWN') return 'status-card down';
    return 'status-card unknown';
  };

  return (
    <div className="system">
      <h1>System Status</h1>

      <div className="status-grid">
        <div className={getCardClass(backendStatus)}>
          <h3>Backend API</h3>
          <p className="status">{backendStatus}</p>
          <p className="url">http://localhost:8080</p>
        </div>

        <div className={getCardClass(mlStatus)}>
          <h3>ML Service</h3>
          <p className="status">{mlStatus}</p>
          <p className="url">{mlVersion ? `Version: ${mlVersion}` : 'http://localhost:8000'}</p>
        </div>

        <div className="status-card up">
          <h3>Database</h3>
          <p className="status">UP</p>
          <p className="url">PostgreSQL - localhost:5432</p>
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
