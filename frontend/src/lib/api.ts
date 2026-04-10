const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('cerno_token');
}

export function setToken(token: string) {
  localStorage.setItem('cerno_token', token);
}

export function clearToken() {
  localStorage.removeItem('cerno_token');
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

export async function apiFetch<T = unknown>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Don't set Content-Type for FormData (browser sets it with boundary)
  const isFormData = options?.body instanceof FormData;
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...headers,
      ...(options?.headers as Record<string, string> || {}),
    },
  });

  if (res.status === 401) {
    clearToken();
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// --- Types ---

export interface IncidentResponse {
  id: number;
  title: string;
  description: string;
  service: string;
  state: string;
  reporter_severity: string | null;
  triage_severity: string | null;
  triage_summary: string | null;
  triage_runbook: string | null;
  confidence: number | null;
  needs_human_review: boolean;
  reasoning_steps: ReasoningStep[] | null;
  evidence_paths: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface ReasoningStep {
  agent: string;
  duration_ms: number;
  tool_calls: { name: string; input: string; output: string }[];
  finding: string;
}

export interface StateTransition {
  incident_id: number;
  from_state: string;
  to_state: string;
  timestamp: string;
  duration_ms: number | null;
  metadata: Record<string, unknown>;
}

// --- Auth ---

export async function register(username: string, password: string) {
  return apiFetch<{ id: number; username: string }>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function login(username: string, password: string) {
  const data = await apiFetch<{ access_token: string; token_type: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  setToken(data.access_token);
  return data;
}

// --- Incidents ---

export async function createIncident(formData: FormData) {
  return apiFetch<IncidentResponse>('/incidents/', {
    method: 'POST',
    body: formData,
  });
}

export async function listIncidents(state?: string) {
  const path = state ? `/incidents/?state=${state}` : '/incidents/';
  return apiFetch<IncidentResponse[]>(path);
}

export async function getIncident(id: number) {
  return apiFetch<IncidentResponse>(`/incidents/${id}`);
}

export async function getTransitions(id: number) {
  return apiFetch<StateTransition[]>(`/incidents/${id}/transitions`);
}
