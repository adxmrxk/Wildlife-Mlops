export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'down';
  service: string;
  timestamp: string;
}

export interface Species {
  id: number;
  name: string;
  commonName: string;
  description: string;
  active: boolean;
}

export interface Prediction {
  id: number;
  imageName: string;
  imageUrl: string;
  predictedSpecies: Species;
  confidence: number;
  modelVersion: string;
  createdAt: string;
}

export interface ClassMetrics {
  support: number;
  correct: number;
  precision: number;
  recall: number;
  f1: number;
}

export interface EvaluationReport {
  model_version: string;
  model_path: string;
  evaluated_at: string;
  samples_per_class: number | string;
  images_scored: number;
  images_skipped: number;
  accuracy: number;
  macro_avg: { precision: number; recall: number; f1: number };
  mean_confidence: number;
  classes: string[];
  confusion_matrix: number[][];
  per_class: Record<string, ClassMetrics>;
  weakest_classes: string[];
  strongest_classes: string[];
}

export interface EvaluationJob {
  status: 'RUNNING' | 'SUCCESS' | 'FAILED' | 'NO_REPORT';
  started_at?: number;
  completed_at?: number;
  report?: EvaluationReport;
  error?: string;
}

export interface BatchItem {
  filename: string;
  predicted_species?: string;
  confidence?: number;
  is_confident?: boolean;
  top_predictions?: { species: string; confidence: number }[];
  error?: string;
}

export interface BatchResult {
  count: number;
  succeeded: number;
  failed: number;
  mean_confidence: number;
  low_confidence_count: number;
  species_distribution: Record<string, number>;
  model_version: string;
  results: BatchItem[];
}

export interface ModelFileInfo {
  path: string;
  size_mb: number;
  modified: string;
}

export interface ModelVersions {
  model_version: string;
  model_loaded: boolean;
  local_files: {
    live: ModelFileInfo | null;
    previous: ModelFileInfo | null;
    candidate: ModelFileInfo | null;
  };
  can_rollback: boolean;
  can_promote: boolean;
  registry: { version: string; run_id: string; status: string; created: string }[];
  registry_error: string | null;
}

export interface RetrainSignal {
  eventType: string;
  reason: string;
  triggeredAt: string;
  recordedAt: string;
}

export interface ReviewQueue {
  threshold: number;
  pendingCount: number;
  pending: Prediction[];
  reviewedCount: number;
  modelCorrectOnReviewed: number;
  reviewedAccuracy: number | null;
  retrainSignals: RetrainSignal[];
}

export interface DashboardStats {
  totalPredictions: number;
  totalSpecies: number;
  averageConfidence: number;
  modelVersion: string;
}
