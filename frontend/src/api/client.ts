import axios from 'axios';

// Extend axios config type to carry per-request metadata
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    metadata?: { startTime: number };
  }
}

// ?? instead of || so empty string (Docker: relative URL via nginx) is kept as-is
const API_BASE_URL = import.meta.env.VITE_API_URL ?? '';
const API_VERSION = import.meta.env.VITE_API_VERSION || '0.1.0';
const TOKEN_KEY = 'sceneiq_token';

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/${API_VERSION}`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: inject Bearer token + record start time for timing
apiClient.interceptors.request.use((config) => {
  config.metadata = { startTime: performance.now() };
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: dev logging with timing + 401 session clearing
apiClient.interceptors.response.use(
  (response) => {
    if (import.meta.env.DEV) {
      const ms = response.config.metadata
        ? Math.round(performance.now() - response.config.metadata.startTime)
        : '?';
      console.log(
        `[${response.status}] ${response.config.method?.toUpperCase()} ${response.config.url} — ${ms}ms`,
      );
    }
    return response;
  },
  (error) => {
    if (import.meta.env.DEV) {
      const status = error.response?.status ?? 'ERR';
      const ms = error.config?.metadata
        ? Math.round(performance.now() - error.config.metadata.startTime)
        : '?';
      console.warn(
        `[${status}] ${error.config?.method?.toUpperCase()} ${error.config?.url} — ${ms}ms`,
        error.message,
      );
    }
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      window.location.href = '/';
    }
    return Promise.reject(error);
  },
);

export function getApiUrl(endpoint: string): string {
  return `/api/${API_VERSION}/${endpoint}`;
}

export default apiClient;
