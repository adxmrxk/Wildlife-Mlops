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

export interface DashboardStats {
  totalPredictions: number;
  totalSpecies: number;
  averageConfidence: number;
  modelVersion: string;
}
