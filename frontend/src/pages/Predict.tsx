import { useState } from 'react';
import './Predict.css';

function Predict() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

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
        </div>
      )}
    </div>
  );
}

export default Predict;
