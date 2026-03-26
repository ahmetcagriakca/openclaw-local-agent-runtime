/**
 * Typed API client — all endpoints from Sprint 8.
 * Base URL: /api/v1 (Vite proxy handles → :8003).
 */
import type {
  MissionListResponse,
  MissionDetailResponse,
  StageListResponse,
  StageDetail,
  ApprovalListResponse,
  TelemetryListResponse,
  HealthApiResponse,
  CapabilityListResponse,
  MutationResponse,
  CreateMissionResponse,
} from '../types/api'

const BASE = '/api/v1'

class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(`API error ${status}`)
    this.name = 'ApiError'
  }
}

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    let body: unknown
    try {
      body = await res.json()
    } catch {
      body = await res.text()
    }
    throw new ApiError(res.status, body)
  }
  return res.json() as Promise<T>
}

// ── Named endpoint functions ────────────────────────────────────

export function getMissions(): Promise<MissionListResponse> {
  return apiGet<MissionListResponse>('/missions')
}

export function getMission(id: string): Promise<MissionDetailResponse> {
  return apiGet<MissionDetailResponse>(`/missions/${encodeURIComponent(id)}`)
}

export function getStages(missionId: string): Promise<StageListResponse> {
  return apiGet<StageListResponse>(`/missions/${encodeURIComponent(missionId)}/stages`)
}

export function getStage(missionId: string, idx: number): Promise<StageDetail> {
  return apiGet<StageDetail>(`/missions/${encodeURIComponent(missionId)}/stages/${idx}`)
}

export function getApprovals(): Promise<ApprovalListResponse> {
  return apiGet<ApprovalListResponse>('/approvals')
}

export function getTelemetry(missionId?: string): Promise<TelemetryListResponse> {
  const qs = missionId ? `?mission_id=${encodeURIComponent(missionId)}` : ''
  return apiGet<TelemetryListResponse>(`/telemetry${qs}`)
}

export function getHealth(): Promise<HealthApiResponse> {
  return apiGet<HealthApiResponse>('/health')
}

export function getCapabilities(): Promise<CapabilityListResponse> {
  return apiGet<CapabilityListResponse>('/capabilities')
}

export { ApiError }

// ── Mutation POST helpers (Sprint 11) ───────────────────────────

async function apiPost<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tab-Id': getTabId(),
      'X-Session-Id': getSessionId(),
    },
  })
  if (!res.ok) {
    let body: unknown
    try {
      body = await res.json()
    } catch {
      body = await res.text()
    }
    throw new ApiError(res.status, body)
  }
  return res.json() as Promise<T>
}

let _tabId: string | null = null
function getTabId(): string {
  if (!_tabId) {
    _tabId = sessionStorage.getItem('tabId') ?? `tab-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    sessionStorage.setItem('tabId', _tabId)
  }
  return _tabId
}

let _sessionId: string | null = null
function getSessionId(): string {
  if (!_sessionId) {
    _sessionId = localStorage.getItem('sessionId') ?? `sess-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    localStorage.setItem('sessionId', _sessionId)
  }
  return _sessionId
}

export function approveApproval(id: string): Promise<MutationResponse> {
  return apiPost<MutationResponse>(`/approvals/${encodeURIComponent(id)}/approve`)
}

export function rejectApproval(id: string): Promise<MutationResponse> {
  return apiPost<MutationResponse>(`/approvals/${encodeURIComponent(id)}/reject`)
}

export function cancelMission(id: string): Promise<MutationResponse> {
  return apiPost<MutationResponse>(`/missions/${encodeURIComponent(id)}/cancel`)
}

export function retryMission(id: string): Promise<MutationResponse> {
  return apiPost<MutationResponse>(`/missions/${encodeURIComponent(id)}/retry`)
}

// ── Mission Create ──────────────────────────────────────────────

async function apiPostJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tab-Id': getTabId(),
      'X-Session-Id': getSessionId(),
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let respBody: unknown
    try {
      respBody = await res.json()
    } catch {
      respBody = await res.text()
    }
    throw new ApiError(res.status, respBody)
  }
  return res.json() as Promise<T>
}

export function createMission(goal: string, complexity?: string): Promise<CreateMissionResponse> {
  return apiPostJson<CreateMissionResponse>('/missions', { goal, complexity: complexity ?? 'medium' })
}
