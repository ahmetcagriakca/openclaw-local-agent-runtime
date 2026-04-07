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
  RolesResponse,
  TokenReport,
  MissionTemplate,
  CostSummary,
  CostMissionsResponse,
  CostTrendsResponse,
  ProvidersResponse,
  AgentRolesResponse,
  CapabilityMatrixResponse,
  AgentPerformanceResponse,
  ProjectListResponse,
  ProjectDetailResponse,
  ProjectRollupResponse,
  PublishedArtifact,
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

export function getRoles(): Promise<RolesResponse> {
  return apiGet<RolesResponse>('/roles')
}

export function getTokenReport(missionId: string): Promise<TokenReport> {
  return apiGet<TokenReport>(`/missions/${missionId}/token-report`)
}

export { ApiError }

// ── Logs ────────────────────────────────────────────────────────

export interface LogEntry {
  timestamp: string
  level: string
  source: string
  message: string
}

export interface LogsResponse {
  errors: LogEntry[]
  mutations: LogEntry[]
  totalErrors: number
  totalMutations: number
}

export function getRecentLogs(): Promise<LogsResponse> {
  return apiGet<LogsResponse>('/logs/recent')
}

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
    _tabId = sessionStorage.getItem('tabId') ?? `tab-${Date.now()}-${crypto.randomUUID().slice(0, 8)}`
    sessionStorage.setItem('tabId', _tabId)
  }
  return _tabId
}

let _sessionId: string | null = null
function getSessionId(): string {
  if (!_sessionId) {
    _sessionId = localStorage.getItem('sessionId') ?? `sess-${Date.now()}-${crypto.randomUUID().slice(0, 8)}`
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

export function pauseMission(id: string): Promise<MutationResponse> {
  return apiPost<MutationResponse>(`/missions/${encodeURIComponent(id)}/pause`)
}

export function resumeMission(id: string): Promise<MutationResponse> {
  return apiPost<MutationResponse>(`/missions/${encodeURIComponent(id)}/resume`)
}

export function skipStage(id: string): Promise<MutationResponse> {
  return apiPost<MutationResponse>(`/missions/${encodeURIComponent(id)}/skip-stage`)
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

export async function deleteSignal(requestId: string): Promise<void> {
  const res = await fetch(`${BASE}/signals/${encodeURIComponent(requestId)}`, {
    method: 'DELETE',
    headers: { 'X-Tab-Id': getTabId(), 'X-Session-Id': getSessionId() },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, body)
  }
}

export function createMission(
  goal: string,
  complexity?: string,
  projectId?: string,
): Promise<CreateMissionResponse> {
  const body: Record<string, unknown> = { goal, complexity: complexity ?? 'medium' }
  if (projectId) body.project_id = projectId
  return apiPostJson<CreateMissionResponse>('/missions', body)
}

export function linkMission(projectId: string, missionId: string): Promise<MutationResponse> {
  return apiPost<MutationResponse>(`/projects/${encodeURIComponent(projectId)}/missions/${encodeURIComponent(missionId)}`)
}

export async function unlinkMission(projectId: string, missionId: string): Promise<void> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(projectId)}/missions/${encodeURIComponent(missionId)}`, {
    method: 'DELETE',
    headers: { 'X-Tab-Id': getTabId(), 'X-Session-Id': getSessionId() },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, body)
  }
}

// ── Templates (B-104) ──────────────────────────────────────────

export function getTemplates(): Promise<MissionTemplate[]> {
  return apiGet<MissionTemplate[]>('/templates')
}

export async function getPresets(): Promise<MissionTemplate[]> {
  const resp = await apiGet<MissionTemplate[] | { presets: MissionTemplate[] }>('/templates/presets')
  // API may return array or {meta, presets, total} — handle both
  if (Array.isArray(resp)) return resp
  if (resp && 'presets' in resp) return resp.presets
  return []
}

export function getTemplate(id: string): Promise<MissionTemplate> {
  return apiGet<MissionTemplate>(`/templates/${encodeURIComponent(id)}`)
}

export function runTemplate(id: string, parameters: Record<string, unknown>): Promise<MutationResponse> {
  return apiPostJson<MutationResponse>(`/templates/${encodeURIComponent(id)}/run`, { parameters })
}

// ── Cost Dashboard (B-105) ────────────────────────────────────

export function getCostSummary(): Promise<CostSummary> {
  return apiGet<CostSummary>('/cost/summary')
}

export function getCostMissions(sort?: string): Promise<CostMissionsResponse> {
  const qs = sort ? `?sort=${encodeURIComponent(sort)}` : ''
  return apiGet<CostMissionsResponse>(`/cost/missions${qs}`)
}

export function getCostTrends(bucket?: string): Promise<CostTrendsResponse> {
  const qs = bucket ? `?bucket=${encodeURIComponent(bucket)}` : ''
  return apiGet<CostTrendsResponse>(`/cost/trends${qs}`)
}

// ── Agent Health (B-108) ──────────────────────────────────────

export function getProviders(): Promise<ProvidersResponse> {
  return apiGet<ProvidersResponse>('/agents/providers')
}

export function getAgentRoles(): Promise<AgentRolesResponse> {
  return apiGet<AgentRolesResponse>('/agents/roles')
}

export function getCapabilityMatrix(): Promise<CapabilityMatrixResponse> {
  return apiGet<CapabilityMatrixResponse>('/agents/capability-matrix')
}

export function getAgentPerformance(): Promise<AgentPerformanceResponse> {
  return apiGet<AgentPerformanceResponse>('/agents/performance')
}

// ── Projects (D-144/D-145) ──────────────────────────────────────

export function createProject(name: string, description?: string, owner?: string): Promise<{ meta: unknown; data: unknown }> {
  return apiPostJson<{ meta: unknown; data: unknown }>('/projects', {
    name,
    description: description ?? '',
    owner: owner ?? 'operator',
  })
}

export function getProjects(params?: {
  status?: string
  search?: string
  sort?: string
}): Promise<ProjectListResponse> {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.search) qs.set('search', params.search)
  if (params?.sort) qs.set('sort', params.sort)
  const query = qs.toString()
  return apiGet<ProjectListResponse>(`/projects${query ? `?${query}` : ''}`)
}

export function getProject(id: string): Promise<ProjectDetailResponse> {
  return apiGet<ProjectDetailResponse>(`/projects/${encodeURIComponent(id)}`)
}

export function getProjectRollup(id: string): Promise<ProjectRollupResponse> {
  return apiGet<ProjectRollupResponse>(`/projects/${encodeURIComponent(id)}/rollup`)
}

export function getProjectArtifacts(id: string): Promise<{ meta: unknown; data: PublishedArtifact[] }> {
  return apiGet<{ meta: unknown; data: PublishedArtifact[] }>(`/projects/${encodeURIComponent(id)}/artifacts`)
}
