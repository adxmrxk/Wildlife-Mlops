import { useEffect, useState } from 'react';

interface Prediction {
  id: number;
  imageName: string;
  predictedSpecies: { name: string; commonName: string };
  confidence: number;
  modelVersion: string;
  createdAt: string;
}

function Predictions() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);

  useEffect(() => {
    fetchPredictions();
  }, []);

  const fetchPredictions = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/predictions');
      const data = await response.json();
      setPredictions(data);
    } catch (error) {
      console.error('Error fetching predictions:', error);
    }
  };

  return (
    <div style={{ padding: '2rem' }}>
      <h1>Prediction History</h1>

      {predictions.length === 0 ? (
        <p>No predictions yet. Upload an image to get started!</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '2rem', background: 'white' }}>
          <thead>
            <tr style={{ background: '#2c3e50', color: 'white' }}>
              <th style={{ padding: '1rem', textAlign: 'left' }}>Image</th>
              <th style={{ padding: '1rem', textAlign: 'left' }}>Species</th>
              <th style={{ padding: '1rem', textAlign: 'left' }}>Confidence</th>
              <th style={{ padding: '1rem', textAlign: 'left' }}>Model Version</th>
              <th style={{ padding: '1rem', textAlign: 'left' }}>Date</th>
            </tr>
          </thead>
          <tbody>
            {predictions.map((pred) => (
              <tr key={pred.id} style={{ borderBottom: '1px solid #ddd' }}>
                <td style={{ padding: '1rem' }}>{pred.imageName}</td>
                <td style={{ padding: '1rem' }}>{pred.predictedSpecies.commonName}</td>
                <td style={{ padding: '1rem' }}>{(pred.confidence * 100).toFixed(1)}%</td>
                <td style={{ padding: '1rem' }}>{pred.modelVersion}</td>
                <td style={{ padding: '1rem' }}>{new Date(pred.createdAt).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default Predictions;
