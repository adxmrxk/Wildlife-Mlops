import { useCallback, useEffect, useRef, useState } from 'react';
import {
  fetchEvaluationJob,
  fetchLatestEvaluation,
  fetchModelVersions,
  promoteModel,
  rollbackModel,
  startEvaluationReport,
} from '../services/api';
import type { EvaluationReport, ModelVersions } from '../types';
import './ModelInsights.css';

const SAMPLE_OPTIONS = [10, 20, 50, 100];

/** Colour a confusion-matrix cell by how much of its row it accounts for. */
function cellStyle(count: number, rowTotal: number, isDiagonal: boolean) {
  if (rowTotal === 0 || count === 0) return {};
  const share = count / rowTotal;
  const hue = isDiagonal ? 152 : 8; // green for correct, red for confusion
  return {
    background: `hsla(${hue}, 70%, 45%, ${0.12 + share * 0.75})`,
    color: share > 0.45 ? '#fff' : undefined,
    fontWeight: share > 0.25 ? 700 : 400,
  };
}

function pct(v: number) {
  return `${(v * 100).toFixed(1)}%`;
}

function ModelInsights() {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [versions, setVersions] = useState<ModelVersions | null>(null);
  const [running, setRunning] = useState(false);
  const [samples, setSamples] = useState(20);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  // Bumped whenever an action changes the deployed model, to refetch versions.
  const [refreshKey, setRefreshKey] = useState(0);
  const loadVersions = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const v = await fetchModelVersions();
        if (!cancelled) setVersions(v);
      } catch {
        if (!cancelled) setVersions(null);
      }
      try {
        const latest = await fetchLatestEvaluation();
        if (!cancelled && 'report' in latest && latest.report) setReport(latest.report);
      } catch {
        /* no report yet — the panel stays empty until one is run */
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  useEffect(
    () => () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    },
    [],
  );

  const runEvaluation = async () => {
    setRunning(true);
    setError(null);
    setNotice(null);
    try {
      const { job_id } = await startEvaluationReport(samples);
      pollRef.current = window.setInterval(async () => {
        try {
          const job = await fetchEvaluationJob(job_id);
          if (job.status === 'SUCCESS' && job.report) {
            setReport(job.report);
            setRunning(false);
            if (pollRef.current) window.clearInterval(pollRef.current);
          } else if (job.status === 'FAILED') {
            setError(job.error ?? 'Evaluation failed');
            setRunning(false);
            if (pollRef.current) window.clearInterval(pollRef.current);
          }
        } catch (e) {
          setError(String(e));
          setRunning(false);
          if (pollRef.current) window.clearInterval(pollRef.current);
        }
      }, 3000);
    } catch (e) {
      setError(String(e));
      setRunning(false);
    }
  };

  const doRollback = async () => {
    setError(null);
    try {
      await rollbackModel();
      setNotice('Rolled back to the previous model and hot-reloaded it.');
      loadVersions();
    } catch (e) {
      setError(`Rollback failed: ${e}`);
    }
  };

  const doPromote = async () => {
    setError(null);
    try {
      const r = await promoteModel();
      setNotice(
        r.promoted_from
          ? `Promoted ${r.promoted_from} to production.`
          : 'No candidate waiting — reloaded the live model.',
      );
      loadVersions();
    } catch (e) {
      setError(`Promotion failed: ${e}`);
    }
  };

  const matrix = report?.confusion_matrix ?? [];
  const classes = report?.classes ?? [];

  return (
    <div className="insights">
      <h1>Model Insights</h1>
      <p className="insights-sub">
        Scores the live model against held-out validation images it never trained on.
        Inference only — this never changes the model.
      </p>

      {/* ── Model version management ─────────────────────────────────── */}
      <section className="panel">
        <h2>Deployed model</h2>
        {versions ? (
          <>
            <div className="version-grid">
              <div className="version-card live">
                <span className="version-label">Live</span>
                <strong>{versions.model_version}</strong>
                <small>
                  {versions.local_files.live
                    ? `${versions.local_files.live.size_mb} MB · ${new Date(
                        versions.local_files.live.modified,
                      ).toLocaleString()}`
                    : 'no file'}
                </small>
                <span className={versions.model_loaded ? 'pill ok' : 'pill bad'}>
                  {versions.model_loaded ? 'loaded' : 'not loaded'}
                </span>
              </div>
              <div className="version-card">
                <span className="version-label">Rollback target</span>
                <strong>{versions.local_files.previous ? 'available' : 'none'}</strong>
                <small>
                  {versions.local_files.previous
                    ? new Date(versions.local_files.previous.modified).toLocaleString()
                    : 'nothing to roll back to'}
                </small>
              </div>
              <div className="version-card">
                <span className="version-label">Candidate</span>
                <strong>{versions.local_files.candidate ? 'waiting' : 'none'}</strong>
                <small>
                  {versions.local_files.candidate
                    ? `${versions.local_files.candidate.size_mb} MB · from last training run`
                    : 'train a model to produce one'}
                </small>
              </div>
            </div>

            <div className="actions">
              <button onClick={doPromote} disabled={!versions.can_promote}>
                Promote candidate
              </button>
              <button onClick={doRollback} disabled={!versions.can_rollback} className="secondary">
                Roll back
              </button>
            </div>

            {versions.registry.length > 0 && (
              <table className="registry">
                <thead>
                  <tr>
                    <th>Registry version</th>
                    <th>Run</th>
                    <th>Status</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.registry.map((v) => (
                    <tr key={v.version}>
                      <td>v{v.version}</td>
                      <td className="mono">{v.run_id.slice(0, 8)}</td>
                      <td>{v.status}</td>
                      <td>{new Date(v.created).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        ) : (
          <p className="muted">ML service unreachable.</p>
        )}
      </section>

      {/* ── Evaluation controls ──────────────────────────────────────── */}
      <section className="panel">
        <h2>Evaluation report</h2>
        <div className="actions">
          <label>
            Images per class
            <select
              value={samples}
              onChange={(e) => setSamples(Number(e.target.value))}
              disabled={running}
            >
              {SAMPLE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <button onClick={runEvaluation} disabled={running}>
            {running ? 'Scoring…' : 'Run evaluation'}
          </button>
          {running && <span className="muted">≈{Math.ceil((samples * 10) / 60)} min on CPU</span>}
        </div>
        {error && <p className="error">{error}</p>}
        {notice && <p className="notice">{notice}</p>}
      </section>

      {report && (
        <>
          <section className="metric-row">
            <div className="metric">
              <span>Accuracy</span>
              <strong>{pct(report.accuracy)}</strong>
            </div>
            <div className="metric">
              <span>Macro F1</span>
              <strong>{report.macro_avg.f1.toFixed(3)}</strong>
            </div>
            <div className="metric">
              <span>Mean confidence</span>
              <strong>{pct(report.mean_confidence)}</strong>
            </div>
            <div className="metric">
              <span>Images scored</span>
              <strong>{report.images_scored}</strong>
            </div>
          </section>

          <section className="panel">
            <h2>Confusion matrix</h2>
            <p className="muted">
              Rows are the true species, columns what the model predicted. The green diagonal
              is correct; red cells off it are where the model confuses one species for another.
            </p>
            <div className="matrix-scroll">
              <table className="matrix">
                <thead>
                  <tr>
                    <th className="corner">actual \ predicted</th>
                    {classes.map((c) => (
                      <th key={c}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {matrix.map((row, i) => {
                    const rowTotal = row.reduce((a, b) => a + b, 0);
                    return (
                      <tr key={classes[i]}>
                        <th>{classes[i]}</th>
                        {row.map((count, j) => (
                          <td key={j} style={cellStyle(count, rowTotal, i === j)}>
                            {count || ''}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel">
            <h2>Per-class performance</h2>
            <table className="per-class">
              <thead>
                <tr>
                  <th>Species</th>
                  <th>Precision</th>
                  <th>Recall</th>
                  <th>F1</th>
                  <th>Correct</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {Object.entries(report.per_class)
                  .sort((a, b) => a[1].f1 - b[1].f1)
                  .map(([name, m]) => (
                    <tr key={name}>
                      <td>{name}</td>
                      <td>{pct(m.precision)}</td>
                      <td>{pct(m.recall)}</td>
                      <td>
                        <div className="f1-bar">
                          <div
                            className="f1-fill"
                            style={{
                              width: `${m.f1 * 100}%`,
                              background:
                                m.f1 > 0.8 ? 'var(--primary)' : m.f1 > 0.6 ? '#d9a441' : '#d9534f',
                            }}
                          />
                          <span>{m.f1.toFixed(3)}</span>
                        </div>
                      </td>
                      <td>
                        {m.correct}/{m.support}
                      </td>
                      <td>
                        {report.weakest_classes.includes(name) && (
                          <span className="pill bad">needs data</span>
                        )}
                        {report.strongest_classes.includes(name) && (
                          <span className="pill ok">strong</span>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
            <p className="muted footnote">
              Precision is how often a prediction of this species is right; recall is how many
              of that species the model actually finds. A class with high precision but low
              recall is being missed, not confused.
            </p>
          </section>
        </>
      )}
    </div>
  );
}

export default ModelInsights;
