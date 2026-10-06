/**
 * SignalFlow API Client & TypeScript Type Definitions
 */

// Resolve base API URL from Vite environment variables (falls back to relative path for dev proxy)
const RAW_API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_BACKEND_URL ||
  '';
const API_BASE = String(RAW_API_BASE).replace(/\/+$/, '');


export interface HealthResponse {
  status: string;
  service: string;
  version?: string;
  environment?: string;
}

export interface RedisHealthResponse {
  status: string;
  service: string;
  connected?: boolean;
}

export interface AnalyticsOverview {
  total_events: number;
  total_errors: number;
  error_rate: number;
  average_latency_ms: number;
}

export interface ServiceMetric {
  service: string;
  event_count: number;
  error_count: number;
  error_rate: number;
  average_latency_ms: number;
}

export interface TimeWindowMetric {
  time_window: string;
  service: string;
  event_type: string;
  event_count: number;
  error_count: number;
  success_count: number;
  error_rate: number;
  average_latency_ms: number;
}

export type SeverityLevel = 'INFO' | 'WARNING' | 'HIGH' | 'CRITICAL';
export type SignalStatus = 'OPEN' | 'RESOLVED';

export interface Anomaly {
  id?: number;
  service: string;
  region: string;
  metric: string;
  anomaly_type: string;
  current_value: number;
  baseline_value: number;
  percentage_change: number;
  z_score?: number | null;
  isolation_score?: number | null;
  severity: SeverityLevel;
  detected_at: string;
  time_window: string;
  reason: string;
}

export interface Signal {
  id: number;
  signal_key: string;
  title: string;
  description: string;
  severity: SeverityLevel;
  service: string;
  region: string;
  status: SignalStatus;
  first_detected_at: string;
  last_detected_at: string;
  created_at: string;
  updated_at: string;
  related_anomalies_count: number;
}

export interface SignalDetail extends Signal {
  anomalies: Anomaly[];
}

export interface AIExplanation {
  signal_id: number;
  summary: string;
  likely_causes: string[];
  recommended_actions: string[];
  model: string;
  generated_at: string;
}

export interface EventItem {
  event_id: string;
  timestamp: string;
  service: string;
  event_type: string;
  region: string;
  status_code: number;
  latency_ms: number;
  value?: number;
  user_id?: string | null;
  ingested_at: string;
}

export interface SimulatorStartRequest {
  scenario: string;
  events_per_second: number;
  duration_seconds: number;
  service?: string;
  region?: string;
}

export interface SimulatorStatusResponse {
  running: boolean;
  scenario: string | null;
  events_generated: number;
  elapsed_seconds: number;
  duration_seconds: number;
  events_per_second: number;
  service: string | null;
  region: string | null;
  message: string | null;
}

export interface SimulatorScenarioItem {
  id: string;
  title: string;
  description: string;
  default_service: string;
  default_region: string;
  expected_anomaly: string | null;
}

export interface ScenariosCatalogResponse {
  scenarios: SimulatorScenarioItem[];
  supported_services: string[];
  supported_regions: string[];
}

export interface PipelineEvaluationResponse {
  anomalies_detected: number;
  signals_created: number;
  signals_updated: number;
}


async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // fallback to status text
    }
    const error = new Error(errorDetail) as Error & { status: number };
    error.status = response.status;
    throw error;
  }

  return response.json();
}

export const api = {
  // Health
  getHealth: () => request<HealthResponse>('/health'),
  getRedisHealth: () => request<RedisHealthResponse>('/health/redis'),

  // Analytics
  getOverview: () => request<AnalyticsOverview>('/api/analytics/overview'),
  getServiceMetrics: () => request<ServiceMetric[]>('/api/analytics/services'),
  getTimeWindows: (windowMinutes: number = 1) =>
    request<TimeWindowMetric[]>(`/api/analytics/windows?window_minutes=${windowMinutes}`),

  // Signals
  getSignals: (params: {
    severity?: string;
    status?: string;
    service?: string;
    region?: string;
    limit?: number;
  } = {}) => {
    const query = new URLSearchParams();
    if (params.severity && params.severity !== 'ALL') query.set('severity', params.severity);
    if (params.status && params.status !== 'ALL') query.set('status', params.status);
    if (params.service && params.service !== 'ALL') query.set('service', params.service);
    if (params.region && params.region !== 'ALL') query.set('region', params.region);
    if (params.limit) query.set('limit', String(params.limit));

    const qs = query.toString();
    return request<Signal[]>(`/api/signals${qs ? `?${qs}` : ''}`);
  },

  getSignal: (id: number) => request<SignalDetail>(`/api/signals/${id}`),

  resolveSignal: (id: number) =>
    request<SignalDetail>(`/api/signals/${id}/resolve`, { method: 'POST' }),

  correlateSignals: () =>
    request<{
      signals_created: number;
      signals_updated: number;
      anomalies_correlated: number;
      signals: Signal[];
    }>('/api/signals/correlate', { method: 'POST' }),

  explainSignal: (id: number) =>
    request<AIExplanation>(`/api/signals/${id}/explain`, { method: 'POST' }),

  // Raw Events
  getEvents: (params: {
    service?: string;
    event_type?: string;
    region?: string;
    status_code?: number;
    limit?: number;
    offset?: number;
  } = {}) => {
    const query = new URLSearchParams();
    if (params.service && params.service !== 'ALL') query.set('service', params.service);
    if (params.event_type && params.event_type !== 'ALL') query.set('event_type', params.event_type);
    if (params.region && params.region !== 'ALL') query.set('region', params.region);
    if (params.status_code) query.set('status_code', String(params.status_code));
    if (params.limit) query.set('limit', String(params.limit));
    if (params.offset) query.set('offset', String(params.offset));

    const qs = query.toString();
    return request<EventItem[]>(`/api/events${qs ? `?${qs}` : ''}`);
  },

  // Simulator Endpoints (Phase 8)
  getSimulatorScenarios: () =>
    request<ScenariosCatalogResponse>('/api/simulator/scenarios'),

  getSimulatorStatus: () =>
    request<SimulatorStatusResponse>('/api/simulator/status'),

  startSimulation: (config: SimulatorStartRequest) =>
    request<SimulatorStatusResponse>('/api/simulator/start', {
      method: 'POST',
      body: JSON.stringify(config),
    }),

  stopSimulation: () =>
    request<SimulatorStatusResponse>('/api/simulator/stop', {
      method: 'POST',
    }),

  evaluateSimulation: () =>
    request<PipelineEvaluationResponse>('/api/simulator/evaluate', {
      method: 'POST',
    }),
};
