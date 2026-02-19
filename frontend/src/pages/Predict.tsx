import { useState } from 'react';
import './Predict.css';

function Predict() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setPreview(URL.createObjectURL(file));
      setResult(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setLoading(true);
    // Placeholder - ML service not implemented yet
    setTimeout(() => {
      setResult({
        species: 'Lion',
        confidence: 0.95,
        message: 'ML service not connected yet. This is a demo result.'
      });
      setLoading(false);
    }, 1500);
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
            accept="image/*"
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

      {result && (
        <div className="result-section">
          <h2>Prediction Result</h2>
          <div className="result-card">
            <p><strong>Species:</strong> {result.species}</p>
            <p><strong>Confidence:</strong> {(result.confidence * 100).toFixed(1)}%</p>
            <p className="demo-note">{result.message}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default Predict;
