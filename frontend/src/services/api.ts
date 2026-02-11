// Wildlife MLOps Platform - API Service
// Centralized API calls to the Spring Boot backend

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api';

export async function fetchHealthStatus() {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
}
