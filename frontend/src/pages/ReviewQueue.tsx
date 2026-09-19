import { useCallback, useEffect, useState } from 'react';
import { fetchAllSpecies, fetchReviewQueue, submitFeedback } from '../services/api';
import type { ReviewQueue as ReviewQueueData, Species } from '../types';
import './ReviewQueue.css';

const THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9];

/** Species the classifier knows about, used when the DB has no rows yet. */
const FALLBACK_SPECIES = [
  'butterfly', 'cat', 'chicken', 'cow', 'dog',
  'elephant', 'horse', 'sheep', 'spider', 'squirrel',
];

function ReviewQueue() {
  const [data, setData] = useState<ReviewQueueData | null>(null);
  const [speciesNames, setSpeciesNames] = useState<string[]>(FALLBACK_SPECIES);
  const [threshold, setThreshold] = useState(0.7);
  const [refreshKey, setRefreshKey] = useState(0);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const q = await fetchReviewQueue(threshold);
        if (!cancelled) setData(q);
      } catch (e) {
        if (!cancelled) setError(`Could not load review queue: ${e}`);
      }
      try {
        const s: Species[] = await fetchAllSpecies();
        if (!cancelled && s.length) {
          // Union of known species and whatever the DB has seen.
          const names = Array.from(new Set([...FALLBACK_SPECIES, ...s.map((x) => x.name)]));
          setSpeciesNames(names.sort());
        }
      } catch {
        /* fall back to the classifier's own label set */
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [threshold, refreshKey]);

  const correct = async (id: number, species: string) => {
    setBusyId(id);
    setError(null);
    try {
      await submitFeedback(id, species);
      setNotice(`Prediction #${id} labelled as "${species}".`);
      refresh();
    } catch (e) {
      setError(`Feedback failed: ${e}`);
    } finally {
      setBusyId(null);
    }
  };

  const reviewedAcc = data?.reviewedAccuracy;

  return (
    <div className="review">
      <h1>Review Queue</h1>
      <p className="review-sub">
        Predictions the model was unsure about. Confirming or correcting them builds a
        labelled set of its real mistakes — and once enough are wrong, the platform raises
        a retraining signal.
      </p>

      {/* ── summary ───────────────────────────────────────────────────── */}
      <section className="summary">
        <div className="stat">
          <span>Awaiting review</span>
          <strong>{data?.pendingCount ?? '—'}</strong>
        </div>
        <div className="stat">
          <span>Reviewed</span>
          <strong>{data?.reviewedCount ?? '—'}</strong>
        </div>
        <div className="stat">
          <span>Model right on reviewed</span>
          <strong>
            {reviewedAcc == null ? '—' : `${(reviewedAcc * 100).toFixed(0)}%`}
          </strong>
        </div>
        <div className="stat">
          <span>Retrain signals</span>
          <strong className={data?.retrainSignals.length ? 'alert' : ''}>
            {data?.retrainSignals.length ?? 0}
          </strong>
        </div>
      </section>

      {/* ── retrain signals ───────────────────────────────────────────── */}
      {data && data.retrainSignals.length > 0 && (
        <section className="panel signal-panel">
          <h2>⚠ Retraining recommended</h2>
          <p className="muted">
            Enough predictions have been marked wrong that the platform flagged the model.
            Training is not started automatically — a run takes hours and would replace the
            live model, so promotion stays a human decision.
          </p>
          <ul className="signals">
            {data.retrainSignals.map((s, i) => (
              <li key={i}>
                <strong>{s.eventType}</strong>
                <span>{s.reason}</span>
                <small>{new Date(s.triggeredAt).toLocaleString()}</small>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ── controls ──────────────────────────────────────────────────── */}
      <section className="panel">
        <div className="actions">
          <label>
            Confidence below
            <select value={threshold} onChange={(e) => setThreshold(Number(e.target.value))}>
              {THRESHOLDS.map((t) => (
                <option key={t} value={t}>
                  {(t * 100).toFixed(0)}%
                </option>
              ))}
            </select>
          </label>
          <button onClick={refresh}>Refresh</button>
        </div>
        {error && <p className="error">{error}</p>}
        {notice && <p className="notice">{notice}</p>}
      </section>

      {/* ── the queue ─────────────────────────────────────────────────── */}
      <section className="panel">
        <h2>Pending predictions</h2>
        {!data ? (
          <p className="muted">Loading…</p>
        ) : data.pending.length === 0 ? (
          <p className="muted">
            Nothing below {(threshold * 100).toFixed(0)}% confidence. Either the model is
            doing well or everything here has already been reviewed.
          </p>
        ) : (
          <table className="queue">
            <thead>
              <tr>
                <th>#</th>
                <th>Image</th>
                <th>Model said</th>
                <th>Confidence</th>
                <th>Actually is…</th>
              </tr>
            </thead>
            <tbody>
              {data.pending.map((p) => (
                <tr key={p.id}>
                  <td className="mono">{p.id}</td>
                  <td className="file">{p.imageName}</td>
                  <td>{p.predictedSpecies?.name ?? '—'}</td>
                  <td>
                    <div className="conf-bar">
                      <div
                        className="conf-fill"
                        style={{
                          width: `${p.confidence * 100}%`,
                          background: p.confidence < 0.4 ? '#d9534f' : '#d9a441',
                        }}
                      />
                      <span>{(p.confidence * 100).toFixed(1)}%</span>
                    </div>
                  </td>
                  <td>
                    <div className="correct-actions">
                      <button
                        className="confirm"
                        disabled={busyId === p.id || !p.predictedSpecies}
                        onClick={() => correct(p.id, p.predictedSpecies!.name)}
                      >
                        ✓ Correct
                      </button>
                      <select
                        defaultValue=""
                        disabled={busyId === p.id}
                        onChange={(e) => {
                          if (e.target.value) correct(p.id, e.target.value);
                        }}
                      >
                        <option value="" disabled>
                          ✗ It&apos;s actually…
                        </option>
                        {speciesNames.map((n) => (
                          <option key={n} value={n}>
                            {n}
                          </option>
                        ))}
                      </select>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default ReviewQueue;
