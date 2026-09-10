const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api';

function getApiTimeout(): number {
  const raw = process.env.NEXT_PUBLIC_API_TIMEOUT_MS;
  if (!raw) return 60000;
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) return 60000;
  return Math.min(parsed, 300000);
}

const DEFAULT_TIMEOUT = getApiTimeout();

export interface UserResponse {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

export class ApiError extends Error {
  status: number;
  detail?: string;
  code?: string;

  constructor(status: number, message: string, detail?: string, code?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.code = code;
  }

  static fromResponse(response: Response, body: unknown): ApiError {
    const bodyRecord = body as Record<string, unknown>;
    const detail = typeof bodyRecord?.detail === 'string' ? bodyRecord.detail : typeof bodyRecord?.message === 'string' ? bodyRecord.message : response.statusText;
    const code = typeof bodyRecord?.code === 'string' ? bodyRecord.code : typeof bodyRecord?.error === 'string' ? bodyRecord.error : undefined;
    return new ApiError(response.status, detail || `API error: ${response.status}`, detail, code);
  }
}

interface RequestOptions extends RequestInit {
  timeout?: number;
  retries?: number;
}

async function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function fetchWithTimeout(url: string, options: RequestOptions = {}): Promise<Response> {
  const { timeout = DEFAULT_TIMEOUT, ...fetchOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
    });
    return response;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError(408, 'La requête a expiré. Veuillez réessayer.', 'Request timeout');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function fetchAPI<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getAuthToken();
  const { retries = 0, timeout = DEFAULT_TIMEOUT, ...fetchOptions } = options;

  const isMutation = ['POST', 'PATCH', 'DELETE', 'PUT'].includes((fetchOptions.method || 'GET').toUpperCase());
  const maxRetries = isMutation ? 0 : retries;

  if (typeof window !== 'undefined') {
    console.debug('[API]', fetchOptions.method || 'GET', url, 'timeout:', timeout);
  }

  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetchWithTimeout(url, {
        ...fetchOptions,
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...fetchOptions.headers,
        },
        timeout,
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
          throw new ApiError(401, 'Non autorisé', 'Token expiré ou invalide');
        }

        if (response.status === 403) {
          throw new ApiError(403, 'Accès refusé', 'Permissions insuffisantes');
        }

        if (response.status === 404) {
          throw new ApiError(404, 'Ressource introuvable', 'Not found');
        }

        let body: unknown = {};
        try {
          body = await response.json();
        } catch {
          // ignore JSON parse errors
        }

        throw ApiError.fromResponse(response, body);
      }

      if (response.status === 204) {
        return undefined as T;
      }

      return response.json();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      if (typeof window !== 'undefined') {
        console.error('[API ERROR]', fetchOptions.method || 'GET', url, error);
      }

      if (error instanceof ApiError && error.status !== 0 && error.status !== 408 && error.status < 500) {
        throw lastError;
      }

      if (attempt < maxRetries) {
        await sleep(Math.pow(2, attempt) * 1000);
      }
    }
  }

  throw lastError || new Error('Requête API échouée');
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await fetchWithTimeout(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
    timeout: 15000,
  });

  if (!res.ok) {
    let body: Record<string, unknown> = {};
    try {
      body = await res.json();
    } catch {
      // ignore
    }
    throw ApiError.fromResponse(res, body);
  }

  return res.json();
}

export function getCurrentUser(): UserResponse | null {
  if (typeof window === 'undefined') return null;
  const user = localStorage.getItem('user');
  return user ? JSON.parse(user) : null;
}

export function logout(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  }
}

export { fetchAPI };
