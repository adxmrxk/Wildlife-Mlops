import { useRef, useState } from 'react';
import { predictBatch } from '../services/api';
import type { BatchResult } from '../types';
import './BatchPredict.css';

const MAX_FILES = 100;

function BatchPredict() {
  const [files, setFiles] = useState<File[]>([]);
  const [result, setResult] = useState<BatchResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const accept = (list: FileList | null) => {
    if (!list) return;
    const images = Array.from(list)
      .filter((f) => f.type.startsWith('image/'))
      .slice(0, MAX_FILES);
    setFiles(images);
    setResult(null);
    setError(images.length ? null : 'No image files in that selection.');
  };

  const run = async () => {
    if (!files.length) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await predictBatch(files));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const sorted = result
    ? [...result.results].sort((a, b) => (a.confidence ?? -1) - (b.confidence ?? -1))
    : [];

  return (
    <div className="batch">
      <h1>Batch Prediction</h1>
      <p className="batch-sub">
        Classify up to {MAX_FILES} images in a single request. Results are sorted
        least-confident first, so the ones worth checking are at the top.
      </p>

      <div
        className={`dropzone${dragging ? ' dragging' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          accept(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={(e) => accept(e.target.files)}
        />
        <p className="drop-title">Drop images here</p>
        <p className="muted">or click to choose files</p>
        {files.length > 0 && (
          <p className="chosen">
            {files.length} image{files.length === 1 ? '' : 's'} ready
          </p>
        )}
      </div>

      <div className="actions">
        <button onClick={run} disabled={!files.length || busy}>
          {busy ? `Classifying ${files.length}…` : `Classify ${files.length || ''} images`}
        </button>
        {files.length > 0 && (
          <button
            className="secondary"
            onClick={() => {
              setFiles([]);
              setResult(null);
            }}
            disabled={busy}
          >
            Clear
          </button>
        )}
      </div>

      {error && <p className="error">{error}</p>}

      {result && (
        <>
          <section className="summary">
            <div className="stat">
              <span>Classified</span>
              <strong>{result.succeeded}</strong>
            </div>
            <div className="stat">
              <span>Failed</span>
              <strong>{result.failed}</strong>
            </div>
            <div className="stat">
              <span>Mean confidence</span>
              <strong>{(result.mean_confidence * 100).toFixed(1)}%</strong>
            </div>
            <div className="stat">
              <span>Low confidence</span>
              <strong>{result.low_confidence_count}</strong>
            </div>
          </section>

          <section className="panel">
            <h2>Species distribution</h2>
            {Object.entries(result.species_distribution)
              .sort((a, b) => b[1] - a[1])
              .map(([species, count]) => (
                <div className="dist-row" key={species}>
                  <span className="dist-name">{species}</span>
                  <div className="dist-track">
                    <div
                      className="dist-fill"
                      style={{ width: `${(count / result.succeeded) * 100}%` }}
                    />
                  </div>
                  <span className="dist-count">{count}</span>
                </div>
              ))}
          </section>

          <section className="panel">
            <h2>Results</h2>
            <table className="results">
              <thead>
                <tr>
                  <th>File</th>
                  <th>Prediction</th>
                  <th>Confidence</th>
                  <th>Runner-up</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((r) => (
                  <tr key={r.filename} className={r.error ? 'row-error' : ''}>
                    <td className="file">{r.filename}</td>
                    <td>{r.error ? <span className="err">{r.error}</span> : r.predicted_species}</td>
                    <td>
                      {r.confidence != null && (
                        <span className={r.is_confident ? 'conf ok' : 'conf low'}>
                          {(r.confidence * 100).toFixed(1)}%
                        </span>
                      )}
                    </td>
                    <td className="muted">
                      {r.top_predictions && r.top_predictions[1]
                        ? `${r.top_predictions[1].species} ${(
                            r.top_predictions[1].confidence * 100
                          ).toFixed(0)}%`
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  );
}

export default BatchPredict;
