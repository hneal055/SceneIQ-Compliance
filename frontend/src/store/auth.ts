import { create } from 'zustand';

const TOKEN_KEY = 'sceneiq_token';
const API_BASE = import.meta.env.VITE_API_URL ?? '';
const API_VERSION = import.meta.env.VITE_API_VERSION || '0.1.0';
const API_PREFIX = `/api/${API_VERSION}`;

interface AuthUser {
  id: string;
  email: string;
  role: string;
}

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loadFromStorage: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      // Use raw fetch to avoid circular dependency with apiClient
      const res = await fetch(`${API_BASE}${API_PREFIX}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? 'Login failed');
      }

      const { access_token } = await res.json();

      // Decode payload (no crypto verify — trust the server; client just reads claims)
      const [, payloadB64] = access_token.split('.');
      const payload = JSON.parse(atob(payloadB64.replace(/-/g, '+').replace(/_/g, '/')));

      const user: AuthUser = {
        id: payload.sub,
        email: payload.email,
        role: payload.role ?? 'admin',
      };

      localStorage.setItem(TOKEN_KEY, access_token);
      set({ user, token: access_token, isAuthenticated: true, isLoading: false, error: null });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed';
      set({ isLoading: false, error: message, isAuthenticated: false });
    }
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    set({ user: null, token: null, isAuthenticated: false, error: null });
  },

  loadFromStorage: () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return;

    try {
      const [, payloadB64] = token.split('.');
      const payload = JSON.parse(atob(payloadB64.replace(/-/g, '+').replace(/_/g, '/')));

      // Check expiry
      if (payload.exp && Date.now() / 1000 > payload.exp) {
        localStorage.removeItem(TOKEN_KEY);
        return;
      }

      const user: AuthUser = {
        id: payload.sub,
        email: payload.email,
        role: payload.role ?? 'admin',
      };

      set({ user, token, isAuthenticated: true });
    } catch {
      localStorage.removeItem(TOKEN_KEY);
    }
  },
}));
