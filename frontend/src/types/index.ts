// Wildlife MLOps Platform - Type Definitions
// Add shared TypeScript types and interfaces here

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'down';
  timestamp: string;
}
