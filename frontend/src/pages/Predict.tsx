import { useState } from 'react';
import './Predict.css';

const SPECIES = ['butterfly', 'cat', 'chicken', 'cow', 'dog', 'elephant', 'horse', 'sheep', 'spider', 'squirrel'];

function Predict() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [feedbackState, setFeedbackState] = useState<'idle' | 'wrong' | 'submitted'>('idle');
  const [correctSpecies, setCorrectSpecies] = useState<string>('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setPreview(URL.createObjectURL(file));
      setResult(null);
      setError('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('image', selectedFile);

      const response = await fetch('http://localhost:8080/api/predictions/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Prediction failed');
      }

      setResult(data);
      setFeedbackState('idle');
      setCorrectSpecies('');
    } catch (err: any) {
      setError(err.message || 'Failed to connect to backend. Make sure the backend and ML service are running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="predict">
      <h1>Predict Wildlife Species</h1>

      <form onSubmit={handleSubmit} className="predict-form">
        <div className="file-input-wrapper">
          <label htmlFor="image-upload" className="file-label">
            Choose Image
          </label>
          <input
            id="image-upload"
            type="file"
            accept="image/jpeg,image/jpg,image/png"
            onChange={handleFileChange}
          />
        </div>

        {preview && (
          <div className="preview-section">
            <img src={preview} alt="Preview" className="preview-image" />
          </div>
        )}

        <button
          type="submit"
          className="predict-button"
          disabled={!selectedFile || loading}
        >
          {loading ? 'Processing...' : 'Predict Species'}
        </button>
      </form>

      {error && (
        <div className="error-section">
          <p className="error-message">{error}</p>
        </div>
      )}

      {result && (
        <div className="result-section">
          <h2>Prediction Result</h2>
          <div className="result-card">
            <p><strong>Species:</strong> {result.predictedSpecies?.name || result.predictedSpecies?.commonName}</p>
            <p><strong>Confidence:</strong> {((result.confidence || 0) * 100).toFixed(1)}%</p>
            <p><strong>Model Version:</strong> {result.modelVersion}</p>
            <p><strong>Image:</strong> {result.imageName}</p>
          </div>

          {result.heatmapBase64 && (
            <div className="heatmap-section">
              <h3 className="heatmap-title">GradCAM — What the model saw</h3>
              <p className="heatmap-subtitle">Highlighted regions show where the model focused to make its prediction</p>
              <div className="heatmap-images">
                <div className="heatmap-image-wrapper">
                  <span className="heatmap-label">Original</span>
                  <img src={preview} alt="Original" className="heatmap-img" />
                </div>
                <div className="heatmap-image-wrapper">
                  <span className="heatmap-label">Model Focus</span>
                  <img src={`data:image/png;base64,${result.heatmapBase64}`} alt="GradCAM heatmap" className="heatmap-img" />
                </div>
              </div>
            </div>
          )}

          <div className="feedback-section">
            {feedbackState === 'idle' && (
              <>
                <p className="feedback-question">Was this correct?</p>
                <div className="feedback-buttons">
                  <button className="feedback-btn yes" onClick={async () => {
                    await fetch(`http://localhost:8080/api/predictions/${result.id}/feedback`, {
                      method: 'PATCH',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ correctSpecies: result.predictedSpecies?.name || result.predictedSpecies?.commonName }),
                    });
                    setFeedbackState('submitted');
                  }}>
                    Yes
                  </button>
                  <button className="feedback-btn no" onClick={() => setFeedbackState('wrong')}>
                    No
                  </button>
                </div>
              </>
            )}

            {feedbackState === 'wrong' && (
              <div className="feedback-correction">
                <p className="feedback-question">What was the correct species?</p>
                <div className="species-grid">
                  {SPECIES.map(s => (
                    <button
                      key={s}
                      className={`species-chip ${correctSpecies === s ? 'selected' : ''}`}
                      onClick={() => setCorrectSpecies(s)}
                    >
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </button>
                  ))}
                  <button
                    className={`species-chip other ${correctSpecies === 'other' ? 'selected' : ''}`}
                    onClick={() => setCorrectSpecies('other')}
                  >
                    Other
                  </button>
                </div>
                <button
                  className="feedback-btn submit"
                  disabled={!correctSpecies}
                  onClick={async () => {
                    await fetch(`http://localhost:8080/api/predictions/${result.id}/feedback`, {
                      method: 'PATCH',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ correctSpecies }),
                    });
                    setFeedbackState('submitted');
                  }}
                >
                  Submit
                </button>
              </div>
            )}

            {feedbackState === 'submitted' && (
              <p className="feedback-thanks">Thanks for the feedback!</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Predict;
