import axios from 'axios';
import type { HealthStatus, Species, Prediction } from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8080/api',
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

export async function uploadImage(file: File): Promise<Prediction> {
  const formData = new FormData();
  formData.append('image', file);
  const { data } = await api.post('/predictions/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export default api;
