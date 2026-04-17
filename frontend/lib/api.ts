import type {
  PokemonSearchResponse,
  RecognitionSessionStartResponse,
  RecognitionState,
  SelectVideoSourceResponse,
  VideoSourcesResponse,
} from '../types/api';

const DEFAULT_DEV_API_BASE_URL = 'http://localhost:8000';

export function getApiBaseUrl(): string {
  const configuredBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (configuredBaseUrl) {
    return configuredBaseUrl.replace(/\/$/, '');
  }
  if (process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test') {
    return DEFAULT_DEV_API_BASE_URL;
  }
  return '';
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, init);
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getVideoSources(): Promise<VideoSourcesResponse> {
  return request('/api/video/sources');
}

export function selectVideoSource(sourceId: string): Promise<SelectVideoSourceResponse> {
  return request('/api/video/source/select', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_id: sourceId }),
  });
}

export function startRecognitionSession(): Promise<RecognitionSessionStartResponse> {
  return request('/api/recognition/session/start', { method: 'POST' });
}

export function getCurrentRecognition(): Promise<RecognitionState> {
  return request('/api/recognition/current');
}

export function overrideRecognition(side: 'player' | 'opponent', name: string): Promise<RecognitionState> {
  return request('/api/recognition/override', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ side, name }),
  });
}

export function searchPokemon(query: string): Promise<PokemonSearchResponse> {
  return request(`/api/pokemon/search?q=${encodeURIComponent(query)}`);
}
