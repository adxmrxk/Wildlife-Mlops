import { useEffect, useState } from 'react';
import './Predictions.css';

interface Prediction {
  id: number;
  imageName: string;
  predictedSpecies: { name: string; commonName: string };
  confidence: number;
  modelVersion: string;
  createdAt: string;
  correctSpecies?: string;
}

function Predictions() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    fetch('http://localhost:8080/api/predictions')
      .then(r => r.json())
      .then(data => { setPredictions(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const handleClearAll = async () => {
    await fetch('http://localhost:8080/api/predictions', { method: 'DELETE' });
    setPredictions([]);
    setConfirming(false);
  };

  return (
    <div className="predictions-page">
      <div className="predictions-header">
        <h1>Prediction History</h1>
        {predictions.length > 0 && (
          <div className="clear-section">
            {confirming ? (
              <>
                <span className="clear-confirm-text">Are you sure?</span>
                <button className="clear-btn confirm" onClick={handleClearAll}>Yes, clear all</button>
                <button className="clear-btn cancel" onClick={() => setConfirming(false)}>Cancel</button>
              </>
            ) : (
              <button className="clear-btn" onClick={() => setConfirming(true)}>Clear All</button>
            )}
          </div>
        )}
      </div>

      {loading ? (
        <p className="predictions-status">Loading...</p>
      ) : predictions.length === 0 ? (
        <p className="predictions-status">No predictions yet. Upload an image to get started!</p>
      ) : (
        <div className="predictions-table-wrapper">
          <table className="predictions-table">
            <thead>
              <tr>
                <th>Image</th>
                <th>Species</th>
                <th>Confidence</th>
                <th>Correct?</th>
                <th>Model Version</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((pred) => (
                <tr key={pred.id}>
                  <td>{pred.imageName}</td>
                  <td className="species-cell">{pred.predictedSpecies?.name || pred.predictedSpecies?.commonName}</td>
                  <td>
                    <span className={`confidence-badge ${pred.confidence >= 0.7 ? 'high' : pred.confidence >= 0.4 ? 'mid' : 'low'}`}>
                      {(pred.confidence * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td>
                    {pred.correctSpecies
                      ? pred.correctSpecies === (pred.predictedSpecies?.name || pred.predictedSpecies?.commonName)
                        ? <span className="feedback-correct">✓ Correct</span>
                        : <span className="feedback-wrong">✗ {pred.correctSpecies}</span>
                      : <span className="feedback-none">—</span>}
                  </td>
                  <td className="muted">{pred.modelVersion}</td>
                  <td className="muted">{new Date(pred.createdAt).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Predictions;
