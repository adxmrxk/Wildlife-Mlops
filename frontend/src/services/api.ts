import axios from 'axios';
import type {
  HealthStatus,
  Species,
  Prediction,
  EvaluationJob,
  BatchResult,
  ModelVersions,
  ReviewQueue,
} from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8080/api',
});

// The ML service is called directly for model-level operations (evaluation
// reports, batch inference, version management) that never touch the database.
const mlApi = axios.create({
  baseURL: import.meta.env.VITE_ML_URL || 'http://localhost:8000',
});

// Health
export async function fetchHealthStatus(): Promise<HealthStatus> {
  const { data } = await api.get('/health');
  return data;
}

// Species
export async function fetchAllSpecies(): Promise<Species[]> {
  const { data } = await api.get('/species');
  return data;
}

export async function fetchSpeciesById(id: number): Promise<Species> {
  const { data } = await api.get(`/species/${id}`);
  return data;
}

export async function createSpecies(species: Partial<Species>): Promise<Species> {
  const { data } = await api.post('/species', species);
  return data;
}

export async function deleteSpecies(id: number): Promise<void> {
  await api.delete(`/species/${id}`);
}

// Predictions
export async function fetchAllPredictions(): Promise<Prediction[]> {
  const { data } = await api.get('/predictions');
  return data;
}

export async function fetchPredictionById(id: number): Promise<Prediction> {
  const { data } = await api.get(`/predictions/${id}`);
  return data;
}

export async function fetchPredictionsBySpecies(speciesId: number): Promise<Prediction[]> {
  const { data } = await api.get(`/predictions/species/${speciesId}`);
  return data;
}

// gradcam defaults to true here because the Predict page renders the heatmap.
// It roughly triples request time, so callers that don't show it pass false.
export async function uploadImage(file: File, gradcam = true): Promise<Prediction> {
  const formData = new FormData();
  formData.append('image', file);
  const { data } = await api.post(`/predictions/upload?gradcam=${gradcam}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

// ── Human-in-the-loop review queue ─────────────────────────────────────────
export async function fetchReviewQueue(threshold = 0.7): Promise<ReviewQueue> {
  const { data } = await api.get(`/predictions/review-queue?threshold=${threshold}`);
  return data;
}

export async function submitFeedback(id: number, correctSpecies: string): Promise<Prediction> {
  const { data } = await api.patch(`/predictions/${id}/feedback`, { correctSpecies });
  return data;
}

// ── Model evaluation report ────────────────────────────────────────────────
export async function startEvaluationReport(samplesPerClass: number): Promise<{ job_id: string }> {
  const { data } = await mlApi.post(`/evaluate/report?samples_per_class=${samplesPerClass}`);
  return data;
}

export async function fetchEvaluationJob(jobId: string): Promise<EvaluationJob> {
  const { data } = await mlApi.get(`/evaluate/report/${jobId}`);
  return data;
}

export async function fetchLatestEvaluation(): Promise<EvaluationJob | { status: string }> {
  const { data } = await mlApi.get('/evaluate/report');
  return data;
}

// ── Batch prediction ───────────────────────────────────────────────────────
export async function predictBatch(files: File[]): Promise<BatchResult> {
  const formData = new FormData();
  files.forEach((f) => formData.append('images', f));
  const { data } = await mlApi.post('/predict/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

// ── Model versions / rollback ──────────────────────────────────────────────
export async function fetchModelVersions(): Promise<ModelVersions> {
  const { data } = await mlApi.get('/models/versions');
  return data;
}

export async function rollbackModel(): Promise<{ rolled_back: boolean; status: string }> {
  const { data } = await mlApi.post('/models/rollback');
  return data;
}

export async function promoteModel(): Promise<{ promoted_from: string | null; status: string }> {
  const { data } = await mlApi.post('/promote');
  return data;
}

export { mlApi };
export default api;
